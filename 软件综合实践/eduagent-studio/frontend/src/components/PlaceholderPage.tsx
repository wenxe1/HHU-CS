import { ArrowRight, CheckCircle2 } from 'lucide-react'
import type { PlaceholderPageContent } from '../types/learning'

interface PlaceholderPageProps {
  content: PlaceholderPageContent
}

function PlaceholderPage({ content }: PlaceholderPageProps) {
  return (
    <section className="placeholder-page panel">
      <div className="placeholder-copy">
        <h2>{content.title}</h2>
        <p>{content.summary}</p>
      </div>

      <div className="placeholder-grid">
        {content.goals.map((goal) => (
          <div className="placeholder-goal" key={goal}>
            <CheckCircle2 size={18} strokeWidth={2} />
            <span>{goal}</span>
          </div>
        ))}
      </div>

      <div className="milestone-strip">
        <span>{content.nextMilestone}</span>
        <ArrowRight size={18} strokeWidth={2} />
      </div>
    </section>
  )
}

export default PlaceholderPage
