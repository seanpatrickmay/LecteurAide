import { useRouter } from 'next/router'
import Link from 'next/link'
import { useEffect, useState } from 'react'

type Book = { id: string; title: string; author: string }

export default function BookDetail() {
  const router = useRouter()
  const { bookId } = router.query
  const [book, setBook] = useState<Book | null>(null)
  useEffect(() => {
    if (!bookId) return
    fetch(process.env.NEXT_PUBLIC_API_URL + '/books')
      .then((r) => r.json())
      .then((books: Book[]) => setBook(books.find((b) => b.id === bookId) || null))
  }, [bookId])
  if (!book) return <div className="p-4">Loading...</div>
  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold">{book.title}</h1>
      <p className="text-sm mb-4">by {book.author}</p>
      <Link href={`/books/${book.id}/scene/1`} className="bg-blue-500 text-white px-4 py-2 rounded">
        Start Reading
      </Link>
    </div>
  )
}
