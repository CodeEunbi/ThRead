import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import { useAccountStore } from './accounts'

export const useChatStore = defineStore('chat', () => {
  const accountStore = useAccountStore()

  const allMessages = ref({})        // { [bookId]: [messages] }
  const currentBookId = ref(null)
  const messages = ref([])
  const error = ref(null)
  const isLoading = ref(false)

  const API_URL = 'http://127.0.0.1:8000'
  const personas = ref({})

  /* =========================
     대화 불러오기
  ========================= */
  const loadConversation = async (bookId) => {
    try {
      console.log('[CHAT] loadConversation:', bookId)

      const res = await axios.post(
        `${API_URL}/api/chat/conversations/`,
        { book_id: bookId },
        {
          headers: {
            Authorization: `Token ${accountStore.token}`,
          },
        }
      )

      const parsedMessages = res.data.messages.map(msg => ({
        sender: msg.is_user ? 'user' : 'bot',
        text: msg.content,
      }))

      allMessages.value[bookId] = parsedMessages
      messages.value = parsedMessages

      console.log('[CHAT] loaded messages:', parsedMessages.length)

    } catch (err) {
      console.error('❌ 대화 불러오기 실패:', err)
      error.value = '이전 대화 불러오기에 실패했어요.'
    }
  }

  /* =========================
     현재 책 선택
  ========================= */
  const setCurrentBook = async (bookId) => {
    console.log('[CHAT] setCurrentBook:', bookId)

    currentBookId.value = bookId

    if (allMessages.value[bookId]) {
      messages.value = allMessages.value[bookId]
    }

    if (!personas.value[bookId]) {
      const personaData = await ensurePersona(bookId)
      if (personaData) {
        personas.value[bookId] = personaData.persona_id
      }
    }
  }

  /* =========================
     페르소나 보장
  ========================= */
  const ensurePersona = async (bookId) => {
    try {
      console.log('[CHAT] ensurePersona:', bookId)

      const res = await axios.post(
        `${API_URL}/api/chat/ensure_persona/`,
        { book_id: bookId },
        {
          headers: {
            Authorization: `Token ${accountStore.token}`,
          },
        }
      )

      console.log('[CHAT] persona ready:', res.data)
      return res.data

    } catch (err) {
      console.error('❌ 페르소나 생성 오류:', err)
      error.value = '페르소나 생성에 실패했어요.'
      return null
    }
  }

  /* =========================
     🔥 메시지 전송
  ========================= */
  const sendMessage = async (question, book) => {
    if (!question.trim()) return
    if (!book || typeof book.pk !== 'number') return

    const bookId = book.pk
    error.value = null
    isLoading.value = true

    console.log('[CHAT] sendMessage')

    // 1️⃣ 유저 메시지 즉시 반영
    const userMessage = { sender: 'user', text: question }
    const current = allMessages.value[bookId] || []

    allMessages.value[bookId] = [...current, userMessage]
    messages.value = allMessages.value[bookId]

    try {
      const res = await axios.post(
        `${API_URL}/api/chat/`,
        { bookId, question },
        {
          headers: {
            Authorization: `Token ${accountStore.token}`,
          },
        }
      )

      console.log('[CHAT] AI response:', res.data)

      // 2️⃣ AI 응답 반영
      const botMessage = {
        sender: 'bot',
        text: res.data.answer,
      }

      allMessages.value[bookId] = [
        ...allMessages.value[bookId],
        botMessage,
      ]

      messages.value = allMessages.value[bookId]

    } catch (err) {
      console.error('❌ chat api error:', err)
      error.value = 'AI 응답에 실패했어요.'
    } finally {
      isLoading.value = false
    }
  }

  return {
    API_URL,
    messages,
    isLoading,
    error,
    sendMessage,
    setCurrentBook,
    ensurePersona,
    loadConversation,
    allMessages,
    currentBookId,
  }
}, { persist: true })
