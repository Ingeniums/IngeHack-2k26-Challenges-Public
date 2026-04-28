import { getStoredToken } from './api'

const token = getStoredToken()
window.location.replace(token ? '/levels.html' : '/register.html')
