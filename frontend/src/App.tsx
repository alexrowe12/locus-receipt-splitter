import { useState, useRef } from 'react'
import './App.css'

interface Item {
  id: string
  quantity: number
  name: string
  price: number
  assignedTo: string
}

interface NegotiationMessage {
  person: number
  message: string
}

interface Transaction {
  from: string
  fromAddress?: string
  to: string
  toAddress?: string
  amount: number
  status: string
  result?: string
  error?: string
}

function App() {
  // Receipt upload state
  const [items, setItems] = useState<Item[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [error, setError] = useState<string>('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Negotiation state
  const [person1Input, setPerson1Input] = useState<string>('')
  const [person2Input, setPerson2Input] = useState<string>('')
  const [person3Input, setPerson3Input] = useState<string>('')
  const [isNegotiating, setIsNegotiating] = useState<boolean>(false)
  const [transcript, setTranscript] = useState<NegotiationMessage[]>([])
  const [finalAmounts, setFinalAmounts] = useState<any>(null)
  const [total, setTotal] = useState<number>(0)

  // Payment state
  const [isExecutingPayment, setIsExecutingPayment] = useState<boolean>(false)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [showTransactions, setShowTransactions] = useState<boolean>(false)

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsLoading(true)
    setError('')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('http://localhost:8000/upload-receipt', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to process receipt')
      }

      const data = await response.json()

      if (data.success && data.items) {
        setItems(data.items)
        // Reset negotiation state
        setTranscript([])
        setFinalAmounts(null)
        setTransactions([])
        setShowTransactions(false)
      } else {
        throw new Error('Invalid response from server')
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to upload receipt'
      setError(errorMessage)
      console.error('Error uploading receipt:', err)
    } finally {
      setIsLoading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleArgue = async () => {
    setIsNegotiating(true)
    setError('')
    setTranscript([])
    setFinalAmounts(null)
    setTransactions([])
    setShowTransactions(false)

    const requestData = {
      items,
      person1_input: person1Input,
      person2_input: person2Input,
      person3_input: person3Input,
    }

    console.log('Starting negotiation with data:', requestData)

    try {
      const response = await fetch('http://localhost:8000/negotiate-payment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to negotiate payments')
      }

      const data = await response.json()

      console.log('Negotiation response:', data)

      if (data.success && data.transcript && data.final_amounts) {
        setTranscript(data.transcript)
        setFinalAmounts(data.final_amounts)
        setTotal(data.total)
      } else {
        throw new Error('Invalid response from server')
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to negotiate payments'
      setError(errorMessage)
      console.error('Error negotiating payments:', err)
    } finally {
      setIsNegotiating(false)
    }
  }

  const handleExecutePayment = async () => {
    setIsExecutingPayment(true)
    setError('')
    setTransactions([])
    setShowTransactions(false)

    const requestData = {
      person1_amount: finalAmounts.person1,
      person2_amount: finalAmounts.person2,
    }

    console.log('Executing payments with data:', requestData)

    try {
      const response = await fetch('http://localhost:8000/execute-negotiated-payment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to execute payments')
      }

      const data = await response.json()

      console.log('Payment execution response:', data)

      if (data.success && data.transactions) {
        setTransactions(data.transactions)
        setShowTransactions(true)
      } else {
        throw new Error('Invalid response from server')
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to execute payments'
      setError(errorMessage)
      console.error('Error executing payments:', err)
    } finally {
      setIsExecutingPayment(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#1a1a1a] text-white p-8">
      <div className="max-w-4xl mx-auto">
        {/* Upload Button */}
        <div className="flex flex-col items-center mb-8">
          <button
            onClick={handleUploadClick}
            disabled={isLoading}
            className={`bg-teal-400 text-black font-semibold px-8 py-3 rounded-lg hover:bg-teal-500 transition-colors text-lg ${
              isLoading ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {isLoading ? 'Processing...' : 'Upload Receipt'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
          />

          {isLoading && (
            <div className="mt-4 flex items-center gap-3">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-400"></div>
              <span className="text-gray-300">Analyzing receipt...</span>
            </div>
          )}

          {error && (
            <div className="mt-4 bg-red-500/20 border border-red-500 text-red-200 px-4 py-3 rounded-lg max-w-md">
              {error}
            </div>
          )}
        </div>

        {/* Items Display */}
        {items.length > 0 && (
          <>
            <div className="bg-[#2d2d2d] rounded-lg p-6 mb-8">
              <h2 className="text-xl font-semibold mb-4">Receipt Items</h2>
              <div className="space-y-2">
                {items.map(item => (
                  <div
                    key={item.id}
                    className="bg-[#404040] rounded-lg px-4 py-3 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-4">
                      <span className="text-gray-400">{item.quantity}x</span>
                      <span className="text-white">{item.name}</span>
                    </div>
                    <span className="text-white font-medium">${item.price.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Person Input Boxes */}
            <div className="space-y-4 mb-8">
              <div className="bg-[#2d2d2d] rounded-lg p-4">
                <label className="block text-teal-400 font-semibold mb-2">Person 1</label>
                <textarea
                  value={person1Input}
                  onChange={(e) => setPerson1Input(e.target.value)}
                  placeholder="Enter your negotiation stance (e.g., 'I'll pay for the americano, but not the cookie...')"
                  className="w-full bg-[#404040] rounded-lg px-4 py-3 text-white placeholder-gray-400 outline-none focus:ring-2 focus:ring-teal-400 min-h-[100px]"
                />
              </div>

              <div className="bg-[#2d2d2d] rounded-lg p-4">
                <label className="block text-teal-400 font-semibold mb-2">Person 2</label>
                <textarea
                  value={person2Input}
                  onChange={(e) => setPerson2Input(e.target.value)}
                  placeholder="Enter your negotiation stance..."
                  className="w-full bg-[#404040] rounded-lg px-4 py-3 text-white placeholder-gray-400 outline-none focus:ring-2 focus:ring-teal-400 min-h-[100px]"
                />
              </div>

              <div className="bg-[#2d2d2d] rounded-lg p-4">
                <label className="block text-teal-400 font-semibold mb-2">Person 3 (Paid upfront)</label>
                <textarea
                  value={person3Input}
                  onChange={(e) => setPerson3Input(e.target.value)}
                  placeholder="Enter your negotiation stance..."
                  className="w-full bg-[#404040] rounded-lg px-4 py-3 text-white placeholder-gray-400 outline-none focus:ring-2 focus:ring-teal-400 min-h-[100px]"
                />
              </div>
            </div>

            {/* Argue Button */}
            <div className="flex flex-col items-center mb-8">
              <button
                onClick={handleArgue}
                disabled={isNegotiating}
                className={`bg-teal-400 text-black font-semibold px-12 py-3 rounded-lg hover:bg-teal-500 transition-colors text-lg ${
                  isNegotiating ? 'opacity-50 cursor-not-allowed' : ''
                }`}
              >
                {isNegotiating ? 'Negotiating...' : 'Argue'}
              </button>

              {isNegotiating && (
                <div className="mt-4 flex items-center gap-3">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-400"></div>
                  <span className="text-gray-300">Agents are negotiating...</span>
                </div>
              )}
            </div>

            {/* Negotiation Transcript */}
            {transcript.length > 0 && (
              <div className="bg-[#2d2d2d] rounded-lg p-6 mb-8">
                <h2 className="text-2xl font-semibold mb-4 text-teal-400">
                  💬 Negotiation Transcript
                </h2>
                <div className="space-y-4">
                  {transcript.map((msg, index) => (
                    <div
                      key={index}
                      className="bg-[#404040] rounded-lg p-4 border-l-4 border-teal-400"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-teal-400 font-semibold">
                          Person {msg.person}
                        </span>
                      </div>
                      <p className="text-gray-200 whitespace-pre-wrap">{msg.message}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Final Amounts Summary */}
            {finalAmounts && (
              <div className="bg-[#2d2d2d] rounded-lg p-6 mb-8">
                <h2 className="text-2xl font-semibold mb-4 text-teal-400">
                  💰 Final Payment Summary
                </h2>
                <div className="space-y-3">
                  <div className="flex justify-between text-white font-semibold text-lg">
                    <span>Total Bill:</span>
                    <span>${total.toFixed(2)}</span>
                  </div>
                </div>

                <div className="mt-6 space-y-3">
                  <div className="bg-[#404040] rounded-lg p-4">
                    <div className="flex justify-between items-center">
                      <span className="text-white font-medium">Person 1 → Person 3:</span>
                      <span className="text-teal-400 font-semibold text-lg">
                        ${finalAmounts.person1.toFixed(2)}
                      </span>
                    </div>
                  </div>
                  <div className="bg-[#404040] rounded-lg p-4">
                    <div className="flex justify-between items-center">
                      <span className="text-white font-medium">Person 2 → Person 3:</span>
                      <span className="text-teal-400 font-semibold text-lg">
                        ${finalAmounts.person2.toFixed(2)}
                      </span>
                    </div>
                  </div>
                  <div className="bg-[#404040] rounded-lg p-4">
                    <div className="flex justify-between items-center">
                      <span className="text-white font-medium">Person 3 (paid upfront):</span>
                      <span className="text-gray-400 font-semibold text-lg">
                        Receives ${(finalAmounts.person1 + finalAmounts.person2).toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Execute Payment Button */}
                <div className="flex flex-col items-center mt-6">
                  <button
                    onClick={handleExecutePayment}
                    disabled={isExecutingPayment}
                    className={`bg-teal-400 text-black font-semibold px-12 py-3 rounded-lg hover:bg-teal-500 transition-colors text-lg ${
                      isExecutingPayment ? 'opacity-50 cursor-not-allowed' : ''
                    }`}
                  >
                    {isExecutingPayment ? 'Executing Payments...' : 'Execute Payment'}
                  </button>

                  {isExecutingPayment && (
                    <div className="mt-4 flex items-center gap-3">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-400"></div>
                      <span className="text-gray-300">Sending USDC payments via Locus...</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Transaction Results */}
            {showTransactions && transactions.length > 0 && (
              <div className="bg-[#2d2d2d] rounded-lg p-6">
                <h2 className="text-2xl font-semibold mb-4 text-teal-400">
                  💸 Payment Results
                </h2>

                <div className="space-y-4">
                  {transactions.map((transaction, index) => (
                    <div
                      key={index}
                      className={`bg-[#404040] rounded-lg p-4 border-l-4 ${
                        transaction.status === 'success'
                          ? 'border-green-500'
                          : 'border-red-500'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            {transaction.status === 'success' ? (
                              <span className="text-green-400 text-xl">✓</span>
                            ) : (
                              <span className="text-red-400 text-xl">✗</span>
                            )}
                            <span className="text-white font-medium">
                              {transaction.from} → {transaction.to}
                            </span>
                          </div>

                          <div className="ml-7 space-y-1 text-sm">
                            <p className="text-gray-300">
                              Amount: <span className="text-white font-medium">${transaction.amount.toFixed(2)} USDC</span>
                            </p>

                            {transaction.fromAddress && (
                              <p className="text-gray-400 truncate">
                                From: {transaction.fromAddress}
                              </p>
                            )}

                            {transaction.toAddress && (
                              <p className="text-gray-400 truncate">
                                To: {transaction.toAddress}
                              </p>
                            )}

                            {transaction.status === 'success' && (
                              <p className="text-green-400 font-medium mt-2">
                                Transaction completed successfully!
                              </p>
                            )}

                            {transaction.status === 'failed' && transaction.error && (
                              <p className="text-red-400 mt-2">
                                Error: {transaction.error}
                              </p>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center">
                          {transaction.status === 'success' ? (
                            <div className="bg-green-500/20 text-green-400 px-3 py-1 rounded text-sm font-medium">
                              Success
                            </div>
                          ) : (
                            <div className="bg-red-500/20 text-red-400 px-3 py-1 rounded text-sm font-medium">
                              Failed
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-6 pt-4 border-t border-gray-600">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-300">
                      Total Transactions: {transactions.length}
                    </span>
                    <div className="flex gap-4">
                      <span className="text-green-400">
                        Successful: {transactions.filter(t => t.status === 'success').length}
                      </span>
                      <span className="text-red-400">
                        Failed: {transactions.filter(t => t.status === 'failed').length}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* Empty State */}
        {items.length === 0 && !isLoading && (
          <div className="text-center text-gray-400 py-12">
            <p className="text-lg">Upload a receipt to get started</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
