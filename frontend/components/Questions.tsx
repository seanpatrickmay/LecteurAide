import { useState } from 'react'

interface Props {
  questions: any[]
  answers: any[]
}

export function Questions({ questions, answers }: Props) {
  const [show, setShow] = useState(false)
  if (!questions || questions.length === 0) return null
  return (
    <div className="mt-6">
      <h2 className="font-semibold mb-2">Questions</h2>
      <ol className="list-decimal ml-6 space-y-1">
        {questions.map((q, i) => (
          <li key={i}>{q}</li>
        ))}
      </ol>
      {answers?.length ? (
        <div className="mt-2">
          <button className="underline" onClick={() => setShow(!show)}>
            {show ? 'Hide answers' : 'Reveal answers'}
          </button>
          {show && (
            <ol className="list-decimal ml-6 mt-2 text-sm text-gray-600">
              {answers.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ol>
          )}
        </div>
      ) : null}
    </div>
  )
}
