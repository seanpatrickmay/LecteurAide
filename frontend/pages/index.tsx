import Link from 'next/link'
import { useEffect, useState } from 'react'
import { ThemeToggle } from '../components/ThemeToggle'

type Book = { id: string; title: string; author: string; cover_url?: string }

export default function Library() {
  const [books, setBooks] = useState<Book[]>([])
  useEffect(() => {
    fetch(process.env.NEXT_PUBLIC_API_URL + '/books')
      .then((r) => r.json())
      .then(setBooks)
  }, [])
  return (
    <div className="p-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Library</h1>
        <ThemeToggle />
      </div>
      <div className="grid md:grid-cols-3 gap-4 mt-4">
        {books.map((b) => (
          <Link key={b.id} href={`/books/${b.id}`} className="border p-2 rounded hover:shadow">
            <div className="font-semibold">{b.title}</div>
            <div className="text-sm">{b.author}</div>
          </Link>
        ))}
      </div>
    </div>
  )
}
