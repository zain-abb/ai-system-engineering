import { Routes, Route } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import { TooltipProvider } from '@/components/ui/tooltip'
import { SettingsProvider } from '@/contexts/SettingsContext'
import { CapabilityStateProvider } from '@/contexts/CapabilityStateContext'
import Dashboard from '@/pages/Dashboard'
import CodeGeneration from '@/pages/CodeGeneration'
import TestGeneration from '@/pages/TestGeneration'
import CodeReview from '@/pages/CodeReview'
import Requirements from '@/pages/Requirements'
import Documentation from '@/pages/Documentation'
import Evaluation from '@/pages/Evaluation'
import Settings from '@/pages/Settings'

function App() {
  return (
    <TooltipProvider>
      <SettingsProvider>
        <CapabilityStateProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/generate" element={<CodeGeneration />} />
              <Route path="/tests" element={<TestGeneration />} />
              <Route path="/review" element={<CodeReview />} />
              <Route path="/requirements" element={<Requirements />} />
              <Route path="/docs" element={<Documentation />} />
              <Route path="/evaluate" element={<Evaluation />} />
              <Route path="/settings" element={<Settings />} />
            </Route>
          </Routes>
        </CapabilityStateProvider>
      </SettingsProvider>
    </TooltipProvider>
  )
}

export default App
