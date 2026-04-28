import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import RegisterPage from './RegisterPage'
import './index.css'
import './styles.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RegisterPage />
  </StrictMode>,
)
