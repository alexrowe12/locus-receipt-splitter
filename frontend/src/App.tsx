import { useState, useRef } from 'react'
import './App.css'

interface Item {
  id: string
  quantity: number
  name: string
  price: number
  assignedTo: string
}

interface Person {
  id: string
  name: string
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
  // Start with empty state
  const [items, setItems] = useState<Item[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [paidBy, setPaidBy] = useState<string>('')
  const [taxPercent, setTaxPercent] = useState<string>('5')
  const [tipPercent, setTipPercent] = useState<string>('20')
  const [newPersonName, setNewPersonName] = useState<string>('')
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [error, setError] = useState<string>('')
  const [isProcessingPayment, setIsProcessingPayment] = useState<boolean>(false)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [showTransactions, setShowTransactions] = useState<boolean>(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  // Calculations
  const subtotal = items.reduce((sum, item) => sum + item.price, 0)
  const taxAmount = subtotal * (parseFloat(taxPercent || '0') / 100)
  const tipAmount = (subtotal + taxAmount) * (parseFloat(tipPercent || '0') / 100)
  const total = subtotal + taxAmount + tipAmount

  // Calculate what each person owes
  const calculateOwed = () => {
    const owedMap: { [key: string]: number } = {}

    if (subtotal === 0) return owedMap

    people.forEach(person => {
      const personItems = items.filter(item => item.assignedTo === person.name)
      const personSubtotal = personItems.reduce((sum, item) => sum + item.price, 0)
      const personTaxTipShare = (personSubtotal / subtotal) * (taxAmount + tipAmount)
      owedMap[person.name] = personSubtotal + personTaxTipShare
    })

    return owedMap
  }

  const owedAmounts = calculateOwed()

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsLoading(true)
    setError('')

    try {
      // Create form data
      const formData = new FormData()
      formData.append('file', file)

      // Send to backend
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
        console.log('Received items from backend:', data)
        console.log('Raw CSV response:', data.raw_response)
        setItems(data.items)
      } else {
        throw new Error('Invalid response from server')
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to upload receipt'
      setError(errorMessage)
      console.error('Error uploading receipt:', err)
    } finally {
      setIsLoading(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleAddPerson = () => {
    if (newPersonName.trim()) {
      setPeople([...people, { id: Date.now().toString(), name: newPersonName.trim() }])
      setNewPersonName('')
    }
  }

  const handleRemovePerson = (personId: string) => {
    const personToRemove = people.find(p => p.id === personId)
    if (personToRemove) {
      // Clear assignments for this person
      setItems(items.map(item =>
        item.assignedTo === personToRemove.name ? { ...item, assignedTo: '' } : item
      ))
      // Remove from people list
      setPeople(people.filter(p => p.id !== personId))
      // Clear paidBy if it was this person
      if (paidBy === personToRemove.name) {
        setPaidBy('')
      }
    }
  }

  const handleRequest = async () => {
    setIsProcessingPayment(true)
    setError('')
    setTransactions([])
    setShowTransactions(false)

    const requestData = {
      items,
      people,
      paidBy,
      subtotal,
      tax: taxAmount,
      tip: tipAmount,
      total,
      owedAmounts,
    }

    console.log('Sending payment request to backend:', requestData)

    try {
      const response = await fetch('http://localhost:8000/request-payment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to process payments')
      }

      const data = await response.json()

      console.log('Payment response:', data)

      if (data.success && data.transactions) {
        setTransactions(data.transactions)
        setShowTransactions(true)
      } else {
        throw new Error('Invalid response from server')
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to process payments'
      setError(errorMessage)
      console.error('Error processing payments:', err)
    } finally {
      setIsProcessingPayment(false)
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
            {isLoading ? 'Processing...' : 'Upload'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
          />

          {/* Loading Spinner */}
          {isLoading && (
            <div className="mt-4 flex items-center gap-3">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-400"></div>
              <span className="text-gray-300">Analyzing receipt...</span>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mt-4 bg-red-500/20 border border-red-500 text-red-200 px-4 py-3 rounded-lg max-w-md">
              {error}
            </div>
          )}
        </div>

        {/* People Management */}
        <div className="bg-[#2d2d2d] rounded-lg p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">People</h2>

          {/* Add Person */}
          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={newPersonName}
              onChange={(e) => setNewPersonName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleAddPerson()}
              placeholder="Add person..."
              className="flex-1 bg-[#404040] rounded-lg px-4 py-2 text-white placeholder-gray-400 outline-none focus:ring-2 focus:ring-teal-400"
            />
            <button
              onClick={handleAddPerson}
              className="bg-teal-400 text-black font-semibold px-6 py-2 rounded-lg hover:bg-teal-500 transition-colors"
            >
              Add
            </button>
          </div>

          {/* People List */}
          {people.length > 0 ? (
            <div className="space-y-2">
              {people.map(person => (
                <div key={person.id} className="flex items-center justify-between bg-[#404040] rounded-lg px-4 py-2">
                  <span>{person.name}</span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPaidBy(person.name)}
                      className={`px-3 py-1 rounded text-sm ${
                        paidBy === person.name
                          ? 'bg-teal-400 text-black'
                          : 'bg-[#505050] text-gray-300 hover:bg-[#606060]'
                      }`}
                    >
                      {paidBy === person.name ? 'Paid ✓' : 'Set as Payer'}
                    </button>
                    <button
                      onClick={() => handleRemovePerson(person.id)}
                      className="text-red-400 hover:text-red-300 px-2 text-xl"
                    >
                      ×
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-400 text-center py-4">
              No people added yet. Add people who shared this receipt.
            </div>
          )}
        </div>

        {/* Items List */}
        {items.length > 0 && (
          <>
            <div className="space-y-3 mb-6">
              {items.map(item => (
                <div
                  key={item.id}
                  className="bg-[#404040] rounded-lg px-6 py-4 flex items-center justify-between"
                >
                  <div className="flex items-center gap-4 flex-1">
                    <span className="text-white font-medium">{item.quantity}</span>
                    <span className="text-white">{item.name}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1">
                      <span className="text-white">$</span>
                      <input
                        type="text"
                        value={item.price.toFixed(2)}
                        onChange={(e) => {
                          const val = e.target.value
                          // Allow numbers and decimals
                          if (val === '' || /^\d*\.?\d*$/.test(val)) {
                            const newPrice = val === '' ? 0 : parseFloat(val)
                            setItems(items.map(i =>
                              i.id === item.id ? { ...i, price: newPrice } : i
                            ))
                          }
                        }}
                        className="bg-[#505050] text-white rounded-lg px-3 py-2 w-24 outline-none focus:ring-2 focus:ring-teal-400 text-right font-medium"
                      />
                    </div>
                    <select
                      value={item.assignedTo}
                      onChange={(e) => {
                        setItems(items.map(i =>
                          i.id === item.id ? { ...i, assignedTo: e.target.value } : i
                        ))
                      }}
                      className={`rounded-lg px-4 py-2 outline-none focus:ring-2 focus:ring-teal-400 cursor-pointer ${
                        item.assignedTo === ''
                          ? 'bg-[#505050] text-gray-400'
                          : 'bg-[#505050] text-white'
                      }`}
                    >
                      <option value="">Select</option>
                      {people.map(person => (
                        <option key={person.id} value={person.name}>
                          {person.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              ))}
            </div>

            {/* Divider */}
            <div className="border-t border-gray-600 my-6"></div>

            {/* Subtotal */}
            <div className="bg-[#404040] rounded-lg px-6 py-4 flex items-center justify-between mb-3">
              <span className="text-white font-medium">Subtotal:</span>
              <div className="flex items-center gap-4">
                <span className="text-white font-medium">${subtotal.toFixed(2)}</span>
                <select
                  value={paidBy}
                  onChange={(e) => setPaidBy(e.target.value)}
                  className={`rounded-lg px-4 py-2 outline-none focus:ring-2 focus:ring-teal-400 cursor-pointer ${
                    paidBy === ''
                      ? 'bg-[#505050] text-gray-400'
                      : 'bg-[#505050] text-white'
                  }`}
                >
                  <option value="">Select</option>
                  {people.map(person => (
                    <option key={person.id} value={person.name}>
                      {person.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Tax */}
            <div className="bg-[#404040] rounded-lg px-6 py-4 flex items-center justify-between mb-3">
              <span className="text-white font-medium">Tax:</span>
              <div className="flex items-center gap-4">
                <span className="text-white font-medium">${taxAmount.toFixed(2)}</span>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={taxPercent}
                    onChange={(e) => {
                      const val = e.target.value
                      if (val === '' || /^\d*\.?\d*$/.test(val)) {
                        setTaxPercent(val)
                      }
                    }}
                    className="bg-[#505050] text-white rounded-lg px-4 py-2 w-20 outline-none focus:ring-2 focus:ring-teal-400 text-right"
                  />
                  <span className="text-white">%</span>
                </div>
              </div>
            </div>

            {/* Tip */}
            <div className="bg-[#404040] rounded-lg px-6 py-4 flex items-center justify-between mb-6">
              <span className="text-white font-medium">Tip:</span>
              <div className="flex items-center gap-4">
                <span className="text-white font-medium">${tipAmount.toFixed(2)}</span>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={tipPercent}
                    onChange={(e) => {
                      const val = e.target.value
                      if (val === '' || /^\d*\.?\d*$/.test(val)) {
                        setTipPercent(val)
                      }
                    }}
                    className="bg-[#505050] text-white rounded-lg px-4 py-2 w-20 outline-none focus:ring-2 focus:ring-teal-400 text-right"
                  />
                  <span className="text-white">%</span>
                </div>
              </div>
            </div>

            {/* Divider */}
            <div className="border-t border-gray-600 my-6"></div>

            {/* Total */}
            <div className="px-6 py-2 flex items-center justify-between mb-6">
              <span className="text-white font-semibold text-xl">Total:</span>
              <span className="text-white font-semibold text-xl">${total.toFixed(2)}</span>
            </div>

            {/* Payment Summary */}
            {paidBy && people.length > 0 && (
              <div className="space-y-3 mb-8">
                {people
                  .filter(person => person.name !== paidBy)
                  .map(person => (
                    <div key={person.id} className="px-6 py-2 flex items-center justify-between">
                      <span className="text-white font-medium">
                        {person.name} pays {paidBy}:
                      </span>
                      <span className="text-white font-semibold text-lg">
                        ${owedAmounts[person.name]?.toFixed(2) || '0.00'}
                      </span>
                    </div>
                  ))}
              </div>
            )}

            {/* Request Button */}
            <div className="flex flex-col items-center gap-4">
              <button
                onClick={handleRequest}
                disabled={isProcessingPayment}
                className={`bg-teal-400 text-black font-semibold px-12 py-3 rounded-lg hover:bg-teal-500 transition-colors text-lg ${
                  isProcessingPayment ? 'opacity-50 cursor-not-allowed' : ''
                }`}
              >
                {isProcessingPayment ? 'Processing Payments...' : 'Request Payment'}
              </button>

              {/* Payment Processing Spinner */}
              {isProcessingPayment && (
                <div className="flex items-center gap-3">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-400"></div>
                  <span className="text-gray-300">Sending USDC payments via Locus...</span>
                </div>
              )}
            </div>

            {/* Transaction Results */}
            {showTransactions && transactions.length > 0 && (
              <div className="mt-8 bg-[#2d2d2d] rounded-lg p-6">
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
