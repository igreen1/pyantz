
import { useEffect } from 'react'
import './App.css'
import JobBoard from './components/JobBoard'
import { useAppSelector } from './store/hooks'

function App() {

  return (
    <>

      <JobBoard />
    </>
  )
}

export default App
