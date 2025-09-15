import Tippy from '@tippyjs/react'
import 'tippy.js/dist/tippy.css'

interface Props {
  i: number
  source: string
  translation?: string
  show: boolean
  onToggle: (i: number) => void
}

export function TooltipSentence({ i, source, translation, show, onToggle }: Props) {
  return (
    <Tippy content={translation || ''} disabled={show}>
      <span className="block cursor-pointer" onClick={() => onToggle(i)}>
        {source}
        {show && translation ? <span className="block text-sm text-gray-500">{translation}</span> : null}
      </span>
    </Tippy>
  )
}
