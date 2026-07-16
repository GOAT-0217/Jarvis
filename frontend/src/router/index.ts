import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false, layout: 'none' },
  },
  {
    path: '/',
    redirect: '/chat',
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/ChatAssistant.vue'),
    meta: { requiresAuth: true, layout: 'default' },
  },
  {
    path: '/chat/:sessionId',
    name: 'ChatSession',
    component: () => import('@/views/ChatAssistant.vue'),
    meta: { requiresAuth: true, layout: 'default' },
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { requiresAuth: true, roles: ['knowledge_admin', 'super_admin'], layout: 'default' },
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('@/views/DocumentList.vue'),
    meta: { requiresAuth: true, roles: ['knowledge_admin', 'super_admin'], layout: 'default' },
  },
  {
    path: '/knowledge/categories',
    name: 'Categories',
    component: () => import('@/views/CategoryManage.vue'),
    meta: { requiresAuth: true, roles: ['knowledge_admin', 'super_admin'], layout: 'default' },
  },
  {
    path: '/users',
    name: 'Users',
    component: () => import('@/views/UserManage.vue'),
    meta: { requiresAuth: true, roles: ['super_admin'], layout: 'default' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SystemSettings.vue'),
    meta: { requiresAuth: true, roles: ['super_admin'], layout: 'default' },
  },
  {
    path: '/audit-logs',
    name: 'AuditLogs',
    component: () => import('@/views/AuditLogs.vue'),
    meta: { requiresAuth: true, roles: ['super_admin'], layout: 'default' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('accessToken')
  const userStr = localStorage.getItem('currentUser')
  const currentUser = userStr ? JSON.parse(userStr) : null

  if (to.meta.requiresAuth !== false && !token) {
    return next('/login')
  }

  if (to.meta.roles && Array.isArray(to.meta.roles)) {
    const allowedRoles = to.meta.roles as string[]
    if (!currentUser || !allowedRoles.includes(currentUser.role)) {
      return next('/chat')
    }
  }

  next()
})

export default router
