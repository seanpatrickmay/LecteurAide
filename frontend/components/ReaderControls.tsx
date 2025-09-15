import Link from 'next/link'
import { useEffect } from 'react'
import { ProgressBar } from './ProgressBar'

export function ReaderControls({ bookId, idx, total = 0 }: { bookId: string; idx: number; total?: number }) {
  const prev = idx > 1 ? idx - 1 : null
  const next = idx + 1
  useEffect(() => {
    fetch(process.env.NEXT_PUBLIC_API_URL + '/progress', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-user-id': 'demo-user',
      },
      body: JSON.stringify({ book_id: bookId, scene_index: idx }),
    })
  }, [bookId, idx])
  return (
    <div className="my-2">
      <div className="flex justify-between text-blue-600 mb-2">
        {prev ? <Link href={`/books/${bookId}/scene/${prev}`}>Prev</Link> : <span />}
        <Link href={`/books/${bookId}/scene/${next}`}>Next</Link>
      </div>
      {total > 0 && <ProgressBar current={idx} total={total} />}
    </div>
  )
}
