import { Button } from "./ui/button"
import { useNavigate } from "react-router-dom"
import { motion, AnimatePresence } from "framer-motion"
import { useEffect, useState } from "react"

export function LandingPage() {
  const navigate = useNavigate()
  const [qrPoints, setQrPoints] = useState<{ x: number; y: number; delay: number }[]>([])
  const [showOverlay, setShowOverlay] = useState(false)

  useEffect(() => {
    // Generate random points for the QR code animation
    const points = Array.from({ length: 80 }, (_) => ({
      x: Math.random() * 100,
      y: Math.random() * 100,
      delay: Math.random() * 0.5
    }))
    setQrPoints(points)
    
    // Show overlay after animation
    setTimeout(() => setShowOverlay(true), 1000)
  }, [])

  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-white to-blue-50">
      {/* Animated Background */}
      <div className="absolute inset-0 opacity-10">
        {qrPoints.map((point, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 bg-[#0f50b5]"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 1, 0] }}
            transition={{
              duration: 2,
              delay: point.delay,
              repeat: Infinity,
              repeatType: "reverse"
            }}
            style={{
              left: `${point.x}%`,
              top: `${point.y}%`
            }}
          />
        ))}
      </div>

      {/* Main Content */}
      <AnimatePresence>
        {showOverlay && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="relative min-h-screen"
          >
            {/* Header */}
            <header className="fixed top-0 w-full z-50 bg-white/80 backdrop-blur-sm border-b border-blue-100">
              <motion.div
                initial={{ y: -100 }}
                animate={{ y: 0 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="container max-w-7xl mx-auto px-4 h-16 flex items-center justify-between"
              >
                <motion.img
                  src="/logo.svg"
                  alt="Phonon"
                  className="h-8"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                />
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Button
                    variant="ghost"
                    onClick={() => navigate('/auth/login')}
                    className="text-[#0f50b5] hover:text-[#ff4d26] hover:bg-[#0f50b5]/5"
                  >
                    Login
                  </Button>
                </motion.div>
              </motion.div>
            </header>

            {/* Hero Section */}
            <main className="relative min-h-screen flex items-center justify-center p-4">
              <div className="absolute inset-0 flex items-center justify-center">
                <motion.div
                  className="w-[600px] h-[600px] rounded-full"
                  style={{
                    background: "radial-gradient(circle, rgba(15,80,181,0.08) 0%, rgba(255,255,255,0) 70%)"
                  }}
                  animate={{
                    scale: [1, 1.2, 1],
                    opacity: [0.5, 0.8, 0.5]
                  }}
                  transition={{
                    duration: 4,
                    repeat: Infinity,
                    ease: "easeInOut"
                  }}
                />
              </div>
              
              <div className="relative z-10 text-center space-y-8">
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.3 }}
                  className="space-y-4"
                >
                  <h1 className="text-7xl font-bold tracking-tight">
                    <span className="text-[#0f50b5]">QR</span>{" "}
                    <span className="bg-gradient-to-r from-[#0f50b5] to-[#ff4d26] text-transparent bg-clip-text">
                      Code System
                    </span>
                  </h1>
                  <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                    Powered by Phonon
                  </p>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.5 }}
                  className="flex justify-center"
                >
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="relative group"
                  >
                    <div className="absolute -inset-1 bg-gradient-to-r from-[#0f50b5] to-[#ff4d26] rounded-lg blur opacity-25 group-hover:opacity-75 transition duration-200" />
                    <Button
                      size="lg"
                      onClick={() => navigate('/auth/login')}
                      className="relative px-8 py-6 text-lg bg-white text-[#0f50b5] hover:text-[#ff4d26] border border-[#0f50b5]/30 group-hover:border-[#ff4d26] transition-all duration-200"
                    >
                      Access Dashboard
                    </Button>
                  </motion.div>
                </motion.div>

                {/* Floating Elements */}
                <div className="absolute inset-0 pointer-events-none">
                  <motion.div
                    className="absolute w-4 h-4 rounded-full bg-[#ff4d26]/20"
                    style={{ top: '20%', left: '20%' }}
                    animate={{ y: [-10, 10, -10], opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 3, repeat: Infinity }}
                  />
                  <motion.div
                    className="absolute w-6 h-6 rounded-full bg-[#0f50b5]/20"
                    style={{ top: '30%', right: '25%' }}
                    animate={{ y: [10, -10, 10], opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 4, repeat: Infinity }}
                  />
                  <motion.div
                    className="absolute w-3 h-3 rounded-full bg-gradient-to-r from-[#0f50b5]/20 to-[#ff4d26]/20"
                    style={{ bottom: '30%', right: '40%' }}
                    animate={{ y: [-5, 5, -5], opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 2.5, repeat: Infinity }}
                  />
                </div>
              </div>
            </main>

            {/* Footer */}
            <footer className="fixed bottom-0 w-full py-4 bg-white/80 backdrop-blur-sm border-t border-blue-100">
              <motion.div
                initial={{ y: 100 }}
                animate={{ y: 0 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="container max-w-7xl mx-auto px-4"
              >
                <div className="flex justify-between items-center">
                  <div className="flex items-center space-x-2">
                    <motion.img
                      src="/logo.svg"
                      alt="Phonon"
                      className="h-5 w-5"
                      whileHover={{ rotate: 360 }}
                      transition={{ duration: 0.5 }}
                    />
                    <span className="text-sm text-gray-600">© 2024 Phonon</span>
                  </div>
                </div>
              </motion.div>
            </footer>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
} 