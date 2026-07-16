import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { login as apiLogin, register as apiRegister } from '@/api/auth'
import type { LoginParams, RegisterParams, CurrentUserData } from '@/api/auth'

const token = ref<string>(localStorage.getItem('accessToken') || '')
const currentUser = ref<CurrentUserData | null>(
  JSON.parse(localStorage.getItem('currentUser') || 'null')
)

export function useAuth() {
  const router = useRouter()

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() =>
    currentUser.value?.role === 'super_admin' || currentUser.value?.role === 'knowledge_admin'
  )
  const isSuperAdmin = computed(() => currentUser.value?.role === 'super_admin')

  async function doLogin(params: LoginParams) {
    const res = await apiLogin(params)
    token.value = res.data.access_token
    currentUser.value = { username: res.data.username, role: res.data.role }
    localStorage.setItem('accessToken', res.data.access_token)
    localStorage.setItem('currentUser', JSON.stringify(currentUser.value))
    router.push('/chat')
  }

  async function doRegister(params: RegisterParams) {
    const res = await apiRegister(params)
    token.value = res.data.access_token
    currentUser.value = { username: res.data.username, role: res.data.role }
    localStorage.setItem('accessToken', res.data.access_token)
    localStorage.setItem('currentUser', JSON.stringify(currentUser.value))
    router.push('/chat')
  }

  function logout() {
    token.value = ''
    currentUser.value = null
    localStorage.removeItem('accessToken')
    localStorage.removeItem('currentUser')
    router.push('/login')
  }

  return {
    token,
    currentUser,
    isAuthenticated,
    isAdmin,
    isSuperAdmin,
    doLogin,
    doRegister,
    logout,
  }
}
