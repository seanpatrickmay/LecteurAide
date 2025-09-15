import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import { VocabList } from '../../../../components/VocabList'
import { Questions } from '../../../../components/Questions'
import { ReaderControls } from '../../../../components/ReaderControls'
import { TooltipSentence } from '../../../../components/TooltipSentence'

interface Sentence { i: number; source: string; translation?: string }
interface ScenePayload {
  sentences: Sentence[]
  vocab: any[]
  questions: any[]
  answers: any[]
}

export default function ScenePage() {
  const router = useRouter()
  const { bookId, idx } = router.query
  const [scene, setScene] = useState<ScenePayload | null>(null)
  const [showTrans, setShowTrans] = useState<Record<number, boolean>>({})

  useEffect(() => {
    if (!bookId || !idx) return
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/books/${bookId}/scenes/${idx}`)
      .then((r) => r.json())
      .then(setScene)
  }, [bookId, idx])

  if (!scene) return <div className="p-4">Loading...</div>

  const toggle = (i: number) => setShowTrans({ ...showTrans, [i]: !showTrans[i] })

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <ReaderControls bookId={bookId as string} idx={Number(idx)} />
      <VocabList items={scene.vocab} />
      <div className="my-4 space-y-2">
        {scene.sentences.map((s) => (
          <TooltipSentence
            key={s.i}
            i={s.i}
            source={s.source}
            translation={s.translation}
            show={!!showTrans[s.i]}
            onToggle={toggle}
          />
        ))}
      </div>
      <Questions questions={scene.questions} answers={scene.answers} />
    </div>
  )
}
