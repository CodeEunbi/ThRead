<template>
  <div class="chat-wrapper">
    <h3 class="chat-title">✍️ 작가에게 질문해보세요</h3>

    <p class="warning">실제 작가가 아님을 알려드립니다</p>
    <p v-if="chatStore.error" class="error">{{ chatStore.error }}</p>

    <!-- 채팅 영역 -->
    <div class="chat-box" ref="chatBox">
      <div
        v-for="(msg, index) in chatStore.messages"
        :key="index"
        :class="['message-row', msg.sender]"
      >
        <div class="bubble">
          {{ msg.text }}
        </div>
      </div>

      <!-- 로딩 중 말풍선 -->
      <div v-if="chatStore.isLoading" class="message-row bot">
        <div class="bubble loading">
          작가가 답변 중입니다…
        </div>
      </div>
    </div>

    <!-- 입력 영역 -->
    <div class="input-row">
      <input
        v-model="question"
        type="text"
        placeholder="질문을 입력하세요"
        @keyup.enter="send"
        :disabled="chatStore.isLoading"
      />
      <button @click="send" :disabled="chatStore.isLoading">
        전송
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { useAccountStore } from '@/stores/accounts'
import booksData from '@/assets/fixtures/books.json'

// 라우터에서 bookId 가져오기
const route = useRoute()
const bookId = parseInt(route.params.bookId)

// fixtures에서 책 찾기
const rawBook = booksData.find(book => book.pk === bookId)
const book = rawBook ? { ...rawBook.fields, pk: rawBook.pk } : null

const chatStore = useChatStore()
const accountStore = useAccountStore()
const question = ref('')
const chatBox = ref(null)

// 초기 로딩
onMounted(async () => {
  if (!book || !book.pk) return

  // 페르소나 보장
  await chatStore.ensurePersona(book.pk)

  // 대화 불러오기
  await chatStore.loadConversation(book.pk)

  // 현재 책 설정
  chatStore.setCurrentBook(book.pk)
})

// bookId 변경 시 메시지 갱신
watch(
  () => bookId,
  () => {
    if (book?.pk) {
      chatStore.setCurrentBook(book.pk)
    }
  },
  { immediate: true }
)

// 메시지 변경 시 자동 스크롤
watch(
  () => chatStore.messages.length,
  async () => {
    await nextTick()
    if (chatBox.value) {
      chatBox.value.scrollTop = chatBox.value.scrollHeight
    }
  }
)

// 메시지 전송
function send() {
  if (!question.value.trim()) return
  chatStore.sendMessage(question.value, book)
  question.value = ''
}
</script>

<style scoped>
.chat-wrapper {
  max-width: 700px;
  margin: 40px auto;
  display: flex;
  flex-direction: column;
  height: 80vh;
}

.chat-title {
  text-align: center;
  margin-bottom: 8px;
}

.warning {
  text-align: center;
  color: gray;
  font-size: 13px;
  margin-bottom: 8px;
}

.error {
  text-align: center;
  color: #ff6b6b;
  font-size: 13px;
  margin-bottom: 8px;
}

/* 채팅 영역 */
.chat-box {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #111;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 메시지 행 */
.message-row {
  display: flex;
}

/* 사용자 메시지 */
.message-row.user {
  justify-content: flex-end;
}

/* 봇 메시지 */
.message-row.bot {
  justify-content: flex-start;
}

/* 말풍선 */
.bubble {
  max-width: 70%;
  padding: 10px 14px;
  border-radius: 14px;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-line;
}

/* 사용자 말풍선 */
.message-row.user .bubble {
  background-color: #d9faff;
  color: #000;
  border-bottom-right-radius: 4px;
}

/* 봇 말풍선 */
.message-row.bot .bubble {
  background-color: #2a2a2a;
  color: #fff;
  border-bottom-left-radius: 4px;
}

/* 로딩 말풍선 */
.bubble.loading {
  font-style: italic;
  opacity: 0.8;
  animation: blink 1.2s infinite;
}

/* 채팅창 스크롤바 */
.chat-box::-webkit-scrollbar {
  width: 8px;
}

/* 스크롤바 트랙 (배경) */
.chat-box::-webkit-scrollbar-track {
  background: #111;       /* 채팅 배경과 동일 */
  border-radius: 10px;
}

/* 스크롤바 핸들 */
.chat-box::-webkit-scrollbar-thumb {
  background-color: #333; /* 어두운 회색 */
  border-radius: 10px;
}

/* hover 시 */
.chat-box::-webkit-scrollbar-thumb:hover {
  background-color: #555;
}


@keyframes blink {
  0% { opacity: 0.3; }
  50% { opacity: 1; }
  100% { opacity: 0.3; }
}

/* 입력 영역 */
.input-row {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.input-row input {
  flex: 1;
  padding: 10px;
  border-radius: 8px;
  border: none;
}

.input-row button {
  padding: 10px 16px;
  border-radius: 8px;
  border: none;
  background: #007aff;
  color: white;
  cursor: pointer;
}

.input-row button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
