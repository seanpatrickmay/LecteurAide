interface VocabItem {
  term?: string
  gloss_en?: string
  pos?: string
  example?: string
}

export function VocabList({ items }: { items: VocabItem[] }) {
  if (!items || items.length === 0) return null
  return (
    <div className="mb-4">
      <h2 className="font-semibold mb-2">Vocabulary</h2>
      <ul className="list-disc ml-6">
        {items.map((v, i) => (
          <li key={i} className="mb-1">
            <span className="font-medium">{v.term}</span> {v.gloss_en && <span>- {v.gloss_en}</span>}
          </li>
        ))}
      </ul>
    </div>
  )
}
