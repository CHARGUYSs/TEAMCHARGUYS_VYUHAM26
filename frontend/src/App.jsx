import { CaregiverWorkspace, PatientDaily } from './CareFeatures';
import MemoryMediaGallery from './MemoryMedia';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  Bell,
  CalendarDays,
  Clock3,
  Heart,
  Home,
  ImageIcon,
  MapPin,
  Mic,
  ShieldAlert,
  Sparkles,
  UserRound,
  Volume2,
  Search,
  Phone,
  Bot,
  Stethoscope,
  Eye,
  CheckCircle2,
  Camera,
  Upload,
  CameraOff,
  Trash2,
  Pencil,
  Fingerprint,
  ScanFace,
  UsersRound,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  RefreshCw,
  Check,
  Menu,
  X,
  BarChart3,
  MessageCircleQuestion,
  TrendingUp,
  Download,
  HelpCircle,
  NotebookPen,
  ClipboardList,
  Timer,
} from 'lucide-react';

const ACTIONS = [
  { id: 'person', title: 'Recognize a face', icon: ScanFace, subtitle:'Identify enrolled loved ones' },
  { id: 'object', title: 'Find my things', icon: Search, subtitle:'Remember where things belong' },
  { id: 'memory', title: 'My memories', icon: ImageIcon, subtitle:'Revisit special moments' },
  { id: 'schedule', title: 'My day', icon: CalendarDays, subtitle:'Stay on top of your routine' },
  { id: 'voice', title: 'Talk to ReMind', icon: Mic, subtitle:'Ask anything about your day' },
  { id: 'help', title: 'Get help', icon: ShieldAlert, subtitle:'Reach a trusted contact' },
];

const defaultPersonForm = {
  name: '',
  relationship: '',
  description: '',
};

const defaultObjectForm = {
  name: '',
  category: 'daily',
  last_location: '',
  notes: '',
};

const defaultMemoryForm = {
  title: '',
  caption: '',
  description: '',
};

const defaultScheduleForm = {
  title: '',
  scheduled_for: '',
  notes: '',
};

const defaultReminderForm = {
  title: '',
  reminder_time: '',
  notes: '',
};

const defaultPreferenceForm = {
  response_mode: 'text',
  voice_first: false,
  detail_level: 'brief',
  reminder_format: 'text',
};

const defaultEmergencyForm = {
  name: '',
  phone: '',
  relationship: 'caregiver',
};

const relationshipLabel = (relationship) => relationship.trim().replace(/^my\s+/i, '');


const CATEGORY_COLORS = {
  person: 'bg-teal-500', object: 'bg-sky-500', schedule: 'bg-indigo-500',
  memory: 'bg-violet-500', reminder: 'bg-amber-500', safety: 'bg-rose-500', general: 'bg-slate-500',
};
function CareInsights({ analytics, busy, error, days, setDays, onReload, onExport, onClear }) {
  const total = analytics?.total_questions || 0;
  const maxDay = Math.max(1, ...(analytics?.daily_questions || []).map(row => row.count));
  const maxCategory = Math.max(1, ...(analytics?.by_category || []).map(row => row.count));
  const stats = [
    { label: 'Questions asked', value: total, icon: MessageCircleQuestion, color: 'text-indigo-700 bg-indigo-50' },
    { label: 'Different questions', value: analytics?.unique_questions || 0, icon: Sparkles, color: 'text-purple-700 bg-purple-50' },
    { label: 'Answered using saved info', value: analytics?.answered_questions || 0, icon: CheckCircle2, color: 'text-teal-700 bg-teal-50' },
    { label: 'Need caregiver input', value: analytics?.unanswered_questions || 0, icon: HelpCircle, color: 'text-amber-700 bg-amber-50' },
  ];
  return (
    <section className="insights-panel panel rounded-[28px] p-5 md:p-7" aria-labelledby="insights-title">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div><p className="eyebrow"><Activity size={14}/> SUPPORT INSIGHTS</p><h3 id="insights-title" className="section-heading">Patient question analytics</h3>
          <p className="mt-2 text-sm text-slate-600">Understand what the patient asks most, and where saved answers could help.</p></div>
        <div className="flex flex-wrap items-center gap-2"><label className="text-sm font-bold text-slate-600" htmlFor="analytics-period">Show</label>
          <select id="analytics-period" className="!w-auto !py-2" value={days} onChange={event=>setDays(Number(event.target.value))}>
            <option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option><option value={0}>All time</option>
          </select>
          <button type="button" onClick={onReload} className="btn-outline !py-2" title="Refresh question data"><RefreshCw size={16}/> Refresh</button></div>
      </div>
      {error && <p className="mt-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-700" role="alert">{error}</p>}
      {busy && <p className="mt-4 text-sm text-slate-500" role="status">Updating insights…</p>}
      <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {stats.map(({label,value,icon:Icon,color})=><div key={label} className="metric-card rounded-2xl border border-slate-100 bg-white p-4"><span className={`inline-flex rounded-xl p-2 ${color}`}><Icon size={21}/></span><div className="mt-3 text-3xl font-black text-slate-900">{value}</div><div className="mt-1 text-xs font-semibold leading-snug text-slate-500">{label}</div></div>)}
      </div>
      {total ? <>
        <div className="mt-5 grid gap-5 xl:grid-cols-2">
          <div className="rounded-2xl border border-slate-100 bg-white p-5">
            <div className="mb-4 flex items-center gap-2"><TrendingUp size={19} className="text-teal-700"/><h4 className="font-extrabold">Questions over time</h4></div>
            <div className="analytics-chart" role="img" aria-label={`Question activity over ${analytics.daily_questions.length} days`}>
              {(analytics.daily_questions || []).map(row => <div key={row.date} title={`${row.date}: ${row.count} questions`} className="analytics-bar-column"><span className="analytics-bar" style={{height: `${Math.max(4, 100 * row.count / maxDay)}%`, opacity: row.count ? 1 : .2}}/></div>)}
            </div><div className="mt-2 flex justify-between text-xs text-slate-400"><span>{analytics.daily_questions?.[0]?.date}</span><span>{analytics.daily_questions?.at(-1)?.date}</span></div>
            <p className="mt-3 text-xs text-slate-500">{days===0?'Chart shows the most recent 14 days.':days>30?'Chart shows the most recent 30 days.':''} Counts record questions entered in ReMind, not the patient's health or ability.</p>
          </div>
          <div className="rounded-2xl border border-slate-100 bg-white p-5">
            <div className="mb-4 flex items-center gap-2"><BarChart3 size={19} className="text-indigo-700"/><h4 className="font-extrabold">Question topics</h4></div>
            <div className="space-y-4">{analytics.by_category.map(item=><div key={item.category}><div className="mb-1.5 flex justify-between text-sm"><span className="font-semibold capitalize">{item.category}</span><span className="text-slate-500">{item.count}</span></div><div className="h-2.5 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full ${CATEGORY_COLORS[item.category] || 'bg-slate-500'}`} style={{width:`${100*item.count/maxCategory}%`}}/></div></div>)}</div>
          </div>
        </div>
        <div className="mt-5 grid gap-5 xl:grid-cols-2">
          <div className="rounded-2xl border border-slate-100 bg-white p-5">
            <div className="mb-4 flex items-center justify-between"><h4 className="font-extrabold">Most repeated questions</h4><span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-bold text-indigo-700">Top {analytics.top_questions.length}</span></div>
            <div className="space-y-2">{analytics.top_questions.map((item,index)=><div className="flex items-start gap-3 rounded-xl bg-slate-50 p-3" key={index}><span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-indigo-100 font-extrabold text-indigo-700">{index+1}</span><span className="min-w-0 flex-1 break-words text-sm font-semibold text-slate-800">{item.question}</span><span className="rounded-lg bg-white px-2 py-1 text-xs font-bold text-slate-600">{item.count}×</span></div>)}</div>
          </div>
          <div className="rounded-2xl border border-slate-100 bg-white p-5">
            <h4 className="mb-4 font-extrabold">Recent patient questions</h4>
            <div className="max-h-80 space-y-2 overflow-y-auto">{analytics.recent_questions.map(item=><div key={item.id} className="flex gap-3 border-b border-slate-100 py-2"><span className={`mt-1 h-2.5 w-2.5 flex-shrink-0 rounded-full ${item.answered?'bg-teal-500':'bg-amber-400'}`}/><div className="min-w-0"><p className="break-words text-sm font-semibold text-slate-800">{item.question}</p><p className="mt-1 text-xs text-slate-500">{new Date(item.asked_at).toLocaleString()} · {item.category} · {item.answered?'Saved answer found':'Information not found'}</p></div></div>)}</div>
          </div>
        </div>
      </> : <div className="mt-5 rounded-2xl border border-dashed border-teal-200 bg-teal-50/50 p-8 text-center"><MessageCircleQuestion className="mx-auto h-10 w-10 text-teal-700"/><h4 className="mt-3 text-lg font-extrabold">No questions recorded yet</h4><p className="mt-1 text-sm text-slate-600">Ask something in the patient interface. The count and repeated questions will appear here.</p></div>}
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5">
        <p className="max-w-xl text-xs leading-relaxed text-slate-500"><ShieldCheck size={14} className="mr-1 inline"/>Question history is private to this local account and can contain personal information. Analytics are usage summaries, not a diagnosis.</p>
        <div className="flex flex-wrap gap-2"><button type="button" onClick={onExport} className="btn-outline !py-2" disabled={!total}><Download size={16}/> Export CSV</button><button type="button" onClick={onClear} className="btn-outline !border-rose-200 !py-2 !text-rose-700" disabled={!total}><Trash2 size={16}/> Clear history</button></div>
      </div>
    </section>
  );
}


const MONITOR_COLOR = {
  question: 'bg-violet-100 text-violet-800', object: 'bg-cyan-100 text-cyan-800', note: 'bg-amber-100 text-amber-800', person: 'bg-emerald-100 text-emerald-800',
};
const readableTime = (at) => at ? new Date(at).toLocaleString(undefined, {dateStyle:'medium', timeStyle:'short'}) : '';

function PatientActivityMonitor({ data, busy, error, days, setDays, onReload, onExport, onClear,
                                  noteText, setNoteText, onAddNote, onDeleteNote }) {
  const [filter, setFilter] = useState('all');
  const items = (data?.timeline || []).filter(item => filter === 'all' || item.kind === filter);
  const maxActivity = Math.max(1, ...(data?.daily_activity || []).map(day => Math.max(day.questions, day.objects)));
  const metrics = [
    {label:'Questions asked', value:data?.question_count || 0, icon:MessageCircleQuestion, tint:'bg-violet-100 text-violet-700'},
    {label:'Object requests', value:data?.object_request_count || 0, icon:Search, tint:'bg-sky-100 text-sky-700'},
    {label:'Different objects', value:data?.unique_objects || 0, icon:Sparkles, tint:'bg-emerald-100 text-emerald-700'},
    {label:'Missing object locations', value:data?.unresolved_object_requests || 0, icon:HelpCircle, tint:'bg-orange-100 text-orange-700'},
    {label:'Saved identity prompts', value:data?.saved_identity_prompts || 0, icon:UsersRound, tint:'bg-pink-100 text-pink-700'},
  ];
  return (
    <section aria-labelledby="patient-monitor-title" className="overflow-hidden rounded-[28px] border border-teal-100 bg-gradient-to-br from-[#f0fbff] via-white to-[#fff7ed] p-5 shadow-lg shadow-sky-100/40 md:p-7">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1.5 text-xs font-black tracking-wide text-teal-800 shadow-sm"><Heart size={14}/> CARE COMPANION</div>
          <h3 id="patient-monitor-title" className="mt-2 text-2xl font-black tracking-tight text-slate-900 md:text-3xl">Patient activity monitor</h3>
          <p className="mt-1 max-w-xl text-sm text-slate-600">Questions and objects the patient asked about, plus helpful caregiver follow-ups. Updated when you refresh.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor="monitor-period" className="text-sm font-bold text-slate-700">Period</label>
          <select id="monitor-period" className="!w-auto !py-2" value={days} onChange={event=>setDays(Number(event.target.value))}>
            <option value={7}>7 days</option><option value={30}>30 days</option><option value={90}>90 days</option><option value={0}>All time</option>
          </select>
          <button type="button" className="btn-outline !py-2" onClick={onReload}><RefreshCw size={16}/> Refresh</button>
        </div>
      </header>
      {error && <p role="alert" className="mt-4 rounded-xl bg-rose-50 p-3 text-rose-800">{error}</p>}
      {busy && <p role="status" className="mt-4 text-sm text-teal-700">Loading patient activity…</p>}
      <div className="mt-6 grid grid-cols-2 gap-3 xl:grid-cols-5">
        {metrics.map(({label,value,icon:Icon,tint})=><div key={label} className="rounded-2xl border border-white bg-white/90 p-4 shadow-sm">
          <div className={`inline-flex rounded-xl p-2.5 ${tint}`}><Icon size={20}/></div>
          <p className="mt-3 text-3xl font-black text-slate-900">{value}</p><p className="mt-1 text-xs font-semibold text-slate-600">{label}</p>
        </div>)}
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-sky-100 bg-white p-5 shadow-sm">
          <div className="mb-3 flex items-center gap-2"><Search size={20} className="text-sky-700"/><h4 className="font-extrabold">Recently asked objects</h4></div>
          {(data?.recent_objects || []).length ? <div className="max-h-72 space-y-2 overflow-y-auto">
            {data.recent_objects.slice(0, 8).map(item=><div className="flex items-center gap-3 rounded-xl bg-sky-50/70 p-3" key={item.id}>
              <div className="rounded-xl bg-white p-2 text-sky-700"><Search size={18}/></div>
              <div className="min-w-0 flex-1"><p className="break-words font-bold capitalize text-slate-900">{item.name}</p>
                <p className="text-xs text-slate-500">{readableTime(item.at)} · {item.source==='finder'?'Object Finder':'Question'}</p></div>
              <span className={`rounded-full px-2 py-1 text-[11px] font-bold ${item.resolved?'bg-emerald-100 text-emerald-700':'bg-amber-100 text-amber-800'}`}>{item.resolved?'Location saved':'Not saved'}</span>
            </div>)}
          </div> : <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No object requests yet. Try asking “Where is my pen?” or tap an object in Find my things.</p>}
        </div>
        <div className="rounded-2xl border border-violet-100 bg-white p-5 shadow-sm">
          <div className="mb-3 flex items-center gap-2"><MessageCircleQuestion size={20} className="text-violet-700"/><h4 className="font-extrabold">Recently asked questions</h4></div>
          {(data?.recent_questions || []).length ? <div className="max-h-72 space-y-2 overflow-y-auto">{data.recent_questions.slice(0,8).map(item=><div key={item.id} className="rounded-xl bg-violet-50/60 p-3">
            <p className="break-words text-sm font-bold text-slate-900">{item.question}</p>
            <p className="mt-1 text-xs text-slate-500">{readableTime(item.at)} · {item.answered?'Answered from saved information':'Needs an answer'} · {item.source}</p>
          </div>)}</div> : <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No questions yet. Questions asked in ReMind will show up here.</p>}
        </div>
        <div className="rounded-2xl border border-teal-100 bg-white p-5 shadow-sm">
          <div className="mb-3 flex items-center gap-2"><BarChart3 size={20} className="text-teal-700"/><h4 className="font-extrabold">Most requested objects</h4></div>
          {(data?.top_objects || []).length ? <div className="space-y-3">{data.top_objects.slice(0, 7).map(item=><div key={item.name}>
            <div className="mb-1 flex justify-between gap-2 text-sm"><span className="font-bold capitalize text-slate-800">{item.name}</span><span className="font-black text-teal-700">{item.count} requests</span></div>
            <div className="h-2.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-teal-400" style={{width:`${Math.max(5, 100*item.count/(data.top_objects[0]?.count||1))}%`}}/></div>
          </div>)}</div> : <p className="text-sm text-slate-500">The most requested items will appear here.</p>}
        </div>
        <div className="rounded-2xl border border-amber-100 bg-white p-5 shadow-sm">
          <div className="mb-3 flex items-center gap-2"><ClipboardList size={20} className="text-amber-700"/><h4 className="font-extrabold">Caregiver follow-ups</h4></div>
          {(data?.needs_attention || []).length ? <div className="max-h-72 space-y-2 overflow-y-auto">{data.needs_attention.map((item,index)=><div key={`${item.kind}-${item.title}-${index}`} className="flex gap-2 rounded-xl bg-amber-50 p-3">
            <AlertCircle size={16} className="mt-0.5 flex-shrink-0 text-amber-700"/><div className="min-w-0 flex-1"><p className="break-words text-sm font-bold text-slate-800">{item.title}</p><p className="mt-1 text-xs text-amber-900">{item.kind==='missing_object'?'Add a saved location':'Add a helpful answer'} · {item.count} time(s)</p></div>
          </div>)}</div> : <p className="text-sm text-slate-500">No missing saved answers or object locations in this period.</p>}
        </div>
      </div>
      <div className="mt-5 rounded-2xl border border-pink-100 bg-white p-5 shadow-sm">
        <h4 className="inline-flex items-center gap-2 font-extrabold"><UsersRound size={19} className="text-pink-700"/> Recently saved identity prompts</h4>
        <p className="mt-1 text-xs text-slate-500">Only appears when the patient chooses “Save this profile reminder” after a possible match. This is not proof that they met the person.</p>
        {(data?.recent_people || []).length ? <div className="mt-3 flex flex-wrap gap-2">{data.recent_people.slice(0,8).map(person=><div key={person.id} className="rounded-xl bg-pink-50 px-4 py-3"><p className="text-sm font-bold text-slate-900">{person.name} · {person.relationship}</p><p className="mt-1 text-xs text-slate-500">{readableTime(person.at)}</p></div>)}</div>
         : <p className="mt-3 text-sm text-slate-500">No saved identity prompts in this period.</p>}
      </div>
      <div className="mt-5 rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2"><h4 className="inline-flex items-center gap-2 font-extrabold"><TrendingUp size={20} className="text-teal-700"/> Daily activity</h4>
          <span className="text-xs font-semibold text-slate-500"><span className="text-violet-700">●</span> Questions &nbsp; <span className="text-sky-600">●</span> Objects</span></div>
        <div className="mt-4 flex h-32 items-end gap-1 overflow-hidden rounded-xl bg-slate-50 px-2 py-3" role="img" aria-label="Question and object request counts by day">
          {(data?.daily_activity || []).map(day=><div key={day.date} className="flex h-full min-w-0 flex-1 items-end justify-center gap-px" title={`${day.date}: ${day.questions} questions and ${day.objects} object requests`}>
            <div className="w-[46%] rounded-t bg-violet-400" style={{height:`${day.questions ? Math.max(5,day.questions/maxActivity*100) : 2}%`}}/>
            <div className="w-[46%] rounded-t bg-sky-400" style={{height:`${day.objects ? Math.max(5,day.objects/maxActivity*100) : 2}%`}}/>
          </div>)}
        </div>
        <div className="mt-1 flex justify-between text-xs text-slate-500"><span>{data?.daily_activity?.[0]?.date || 'No data'}</span><span>{data?.daily_activity?.at(-1)?.date || ''}</span></div>
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2"><h4 className="inline-flex items-center gap-2 font-extrabold"><Timer size={19} className="text-indigo-700"/> Activity timeline</h4>
            <div className="flex flex-wrap gap-1">{[['all','All'],['question','Questions'],['object','Objects'],['person','People'],['note','Notes']].map(([key,label])=><button key={key} type="button" onClick={()=>setFilter(key)} aria-pressed={filter===key} className={`rounded-full px-2.5 py-1.5 text-xs font-bold ${filter===key?'bg-teal-700 text-white':'bg-slate-100 text-slate-700'}`}>{label}</button>)}</div></div>
          {items.length ? <div className="mt-3 max-h-80 space-y-2 overflow-y-auto">{items.slice(0,25).map(item=><div key={item.id} className="flex gap-3 border-b border-slate-100 py-2.5">
            <span className={`mt-0.5 inline-flex h-fit rounded-lg px-2 py-1 text-[11px] font-black capitalize ${MONITOR_COLOR[item.kind]||'bg-slate-100'}`}>{item.kind}</span>
            <div className="min-w-0"><p className="break-words text-sm font-semibold text-slate-800">{item.title}</p><p className="mt-1 text-xs text-slate-500">{readableTime(item.at)} · {item.detail}</p></div>
          </div>)}</div> : <p className="mt-3 text-sm text-slate-500">Nothing to show for this filter.</p>}
        </div>
        <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
          <h4 className="inline-flex items-center gap-2 font-extrabold"><NotebookPen size={19} className="text-orange-700"/> Caregiver notes</h4>
          <p className="mt-1 text-xs text-slate-500">Short notes you explicitly enter. Not medical observations.</p>
          <form className="mt-3 space-y-2" onSubmit={event=>{event.preventDefault(); onAddNote();}}>
            <textarea value={noteText} onChange={event=>setNoteText(event.target.value)} maxLength={400} rows={3} placeholder="e.g., Put the blue pen in the desk organizer" aria-label="New caregiver note" required />
            <button type="submit" disabled={!noteText.trim()} className="rounded-xl bg-teal-700 px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50">Add note</button>
          </form>
          <div className="mt-4 max-h-52 space-y-2 overflow-y-auto">{(data?.notes || []).map(item=><div className="flex gap-2 rounded-xl bg-amber-50 p-3" key={item.id}>
            <div className="min-w-0 flex-1"><p className="break-words text-sm font-semibold text-slate-800">{item.text}</p><p className="mt-1 text-xs text-slate-500">{readableTime(item.at)}</p></div>
            <button type="button" onClick={()=>onDeleteNote(item.id)} className="self-start rounded-lg p-1.5 text-rose-700 hover:bg-rose-100" aria-label="Delete note"><Trash2 size={16}/></button>
          </div>)}{!data?.notes?.length && <p className="text-sm text-slate-500">No notes added.</p>}</div>
        </div>
      </div>
      <footer className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-teal-100 pt-4">
        <p className="max-w-xl text-xs leading-relaxed text-slate-600"><ShieldCheck size={15} className="mr-1 inline"/>In-app requests only. An object request such as “pen” does not mean a camera saw a pen. No background camera recording or medical diagnosis.</p>
        <div className="flex flex-wrap gap-2"><button type="button" className="btn-outline !py-2" onClick={onExport} disabled={!data?.object_request_count}><Download size={16}/> Export object CSV</button>
          <button type="button" className="btn-outline !border-rose-200 !py-2 !text-rose-700" onClick={onClear} disabled={!data?.object_request_count}><Trash2 size={16}/> Clear object history</button></div>
      </footer>
    </section>
  );
}

function App() {
  const [activeView, setActiveView] = useState('home');
  const [session, setSession] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('remind_session') || 'null'); }
    catch { return null; }
  });
  const [loginError, setLoginError] = useState('');
  const [loginBusy, setLoginBusy] = useState(false);
  const [apiError, setApiError] = useState('');
  const [homeData, setHomeData] = useState({ next_activity: 'No scheduled activity', upcoming_reminders: [], preferences: { response_mode: 'text' } });
  const [people, setPeople] = useState([]);
  const [objects, setObjects] = useState([]);
  const [memories, setMemories] = useState([]);
  const [memoryUploading, setMemoryUploading] = useState(null);
  const [schedule, setSchedule] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [preferences, setPreferences] = useState(defaultPreferenceForm);
  const [emergencyContacts, setEmergencyContacts] = useState([]);
  const [auditLog, setAuditLog] = useState([]);
  const [notificationCount, setNotificationCount] = useState(0);
  const [monitoring, setMonitoring] = useState(null);
  const [monitoringDays, setMonitoringDays] = useState(30);
  const [monitoringBusy, setMonitoringBusy] = useState(false);
  const [monitoringError, setMonitoringError] = useState('');
  const [careNote, setCareNote] = useState('');
  const [identityReminderMessage, setIdentityReminderMessage] = useState('');
  const [objectLookupName, setObjectLookupName] = useState('');
  const [objectLookupBusy, setObjectLookupBusy] = useState(false);
  const [objectLookupResult, setObjectLookupResult] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [analyticsDays, setAnalyticsDays] = useState(30);
  const [analyticsBusy, setAnalyticsBusy] = useState(false);
  const [analyticsError, setAnalyticsError] = useState('');
  const [readNamesAloud, setReadNamesAloud] = useState(false);
  const [voiceLanguage, setVoiceLanguage] = useState('en-IN');
  const [cameraCheck, setCameraCheck] = useState('idle');
  const [deleteMessage, setDeleteMessage] = useState('');
  const [editingRecord, setEditingRecord] = useState(null);
  const [editMessage, setEditMessage] = useState('');
  const [assistantAnswer, setAssistantAnswer] = useState('Ask a question like “Who is my daughter?”');
  const [question, setQuestion] = useState('');
  const [questionSource, setQuestionSource] = useState('typed');
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef(null);
  const [familyPhoto, setFamilyPhoto] = useState('');
  const [profileMessage, setProfileMessage] = useState('');
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraMessage, setCameraMessage] = useState('');
  const [personDetected, setPersonDetected] = useState(false);
  const cameraVideoRef = useRef(null);
  const [identityStatus, setIdentityStatus] = useState('');
  const [identityFaceDetected, setIdentityFaceDetected] = useState(null);
  const [identityFaceBoxes, setIdentityFaceBoxes] = useState([]);
  const [recognitionInfo, setRecognitionInfo] = useState({ready:false, enrollments:{}, enrolled_people:0, message:'Checking AI models…'});
  const [enrollConsent, setEnrollConsent] = useState(false);
  const [enrollTarget, setEnrollTarget] = useState(null);
  const [enrollBusy, setEnrollBusy] = useState(false);
  const [setupBusy, setSetupBusy] = useState(false);
  const [setupMessage, setSetupMessage] = useState('');
  const [mobileMenu, setMobileMenu] = useState(false);
  const [identityBusy, setIdentityBusy] = useState(false);
  const [confirmedPerson, setConfirmedPerson] = useState(null);
  const lastAnnouncedRef = useRef(null);
  const [identityCameraActive, setIdentityCameraActive] = useState(false);
  const [identityPhoto, setIdentityPhoto] = useState('');
  const identityVideoRef = useRef(null);
  const identityPhotoUrlRef = useRef(null);
  const identityMatchHistoryRef = useRef([]);
  const speakNamesEnabledRef = useRef(readNamesAloud);
  speakNamesEnabledRef.current = readNamesAloud;

  useEffect(() => () => {
    if (identityPhotoUrlRef.current) URL.revokeObjectURL(identityPhotoUrlRef.current);
    recognitionRef.current?.abort?.();
  }, []);

  const compressDetectionImage = async (file) => {
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      throw new Error('Please choose a JPEG, PNG, or WebP photo.');
    }
    if (file.size > 10 * 1024 * 1024) throw new Error('Image must be smaller than 10 MB.');
    const image = await createImageBitmap(file);
    try {
      const scale = Math.min(1, 1280 / Math.max(image.width, image.height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(image.width * scale));
      canvas.height = Math.max(1, Math.round(image.height * scale));
      canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height);
      return await new Promise((resolve, reject) => canvas.toBlob(
        (blob) => blob ? resolve(blob) : reject(new Error('Could not process image.')),
        'image/jpeg', 0.90,
      ));
    } finally {
      image.close();
    }
  };

  const signIn = async (email, password) => {
    setLoginBusy(true);
    setLoginError('');
    try {
      const response = await fetch('/api/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Sign in failed.');
      sessionStorage.setItem('remind_session', JSON.stringify(data));
      setSession(data);
    } catch (error) {
      setLoginError(error.message || 'Could not sign in. Check your backend connection.');
    } finally { setLoginBusy(false); }
  };

  const startDemo = async () => {
    setLoginBusy(true);
    setLoginError('');
    try {
      const response = await fetch('/api/seed', { method: 'POST' });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Demo is unavailable.');
      }
      await signIn('demo@remindai.app', 'remind123');
    } catch (error) {
      setLoginError(`${error.message} Enable DEMO_MODE in the backend for local demonstrations.`);
    } finally { setLoginBusy(false); }
  };

  const signOut = () => {
    sessionStorage.removeItem('remind_session');
    window.speechSynthesis?.cancel?.();
    setIdentityCameraActive(false);
    setCameraActive(false);
    setActiveView('home');
    setSession(null);
    setPeople([]);
    setObjects([]);
    setMemories([]);
    setSchedule([]);
    setReminders([]);
    setEmergencyContacts([]);
    setIdentityFaceBoxes([]);
    setAnalytics(null);
    setMonitoring(null);
    setObjectLookupResult(null);
  };

  const normalizePhoto = async (file) => {
    if (!file.type.startsWith('image/')) {
      throw new Error('Choose an image file.');
    }
    if (file.size > 10 * 1024 * 1024) {
      throw new Error('Image must be smaller than 10 MB.');
    }

    const image = await createImageBitmap(file);
    const scale = Math.min(1, 1280 / Math.max(image.width, image.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(image.width * scale);
    canvas.height = Math.round(image.height * scale);
    canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height);
    image.close();

    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob((result) => {
        if (result) resolve(result);
        else reject(new Error('Could not process this image.'));
      }, 'image/jpeg', 0.82);
    });
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error('Could not read this image.'));
      reader.readAsDataURL(blob);
    });
  };

  useEffect(() => {
    if (!cameraActive || activeView !== 'dashboard') {
      if (cameraActive) setCameraActive(false);
      return undefined;
    }

    let stream;
    let stopped = false;
    let animationFrame;
    let detecting = false;
    let lastDetectionAt = 0;

    const startCamera = async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setCameraMessage('Camera access is not available in this browser.');
        setCameraActive(false);
        return;
      }

      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: { facingMode: 'user' },
        });
        if (stopped) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        cameraVideoRef.current.srcObject = stream;
        await cameraVideoRef.current.play();
        setCameraMessage('Camera is live. ReMind checks for visible faces; frames are processed by your app and are not saved.');

        const detect = async (timestamp) => {
          if (stopped) return;
          if (!detecting && timestamp - lastDetectionAt > 1200 && cameraVideoRef.current?.readyState >= 2) {
            detecting = true;
            lastDetectionAt = timestamp;
            try {
              const video = cameraVideoRef.current;
              const canvas = document.createElement('canvas');
              const scale = Math.min(1, 640 / Math.max(video.videoWidth, video.videoHeight));
              canvas.width = Math.round(video.videoWidth * scale);
              canvas.height = Math.round(video.videoHeight * scale);
              canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
              const frame = await new Promise((resolve, reject) => {
                canvas.toBlob((blob) => {
                  if (blob) resolve(blob);
                  else reject(new Error('Could not capture a camera frame.'));
                }, 'image/jpeg', 0.65);
              });
              const body = new FormData();
              body.append('frame', frame, 'camera-frame.jpg');
              const response = await fetch('/api/detect-person', { method: 'POST', headers: { Authorization: `Bearer ${session.token}` }, body });
              if (!response.ok) throw new Error('Person detection is unavailable.');
              const result = await response.json();
              if (!stopped) {
                setPersonDetected(result.face_detected);
                setCameraMessage(result.face_detected
                  ? 'A face is visible. ReMind does not identify the person.'
                  : 'No face detected yet. Move closer or improve the lighting.');
              }
            } catch {
              if (!stopped) { setPersonDetected(false); setCameraMessage('Person detection is temporarily unavailable. Camera capture still works.'); }
            } finally {
              detecting = false;
            }
          }
          animationFrame = requestAnimationFrame(detect);
        };
        animationFrame = requestAnimationFrame(detect);
      } catch (error) {
        setCameraMessage(error.name === 'NotAllowedError'
          ? 'Camera permission was denied. Allow camera access in your browser settings, or upload a photo instead.'
          : 'Could not start the camera. Upload a photo instead.');
        setCameraActive(false);
      }
    };

    startCamera();
    return () => {
      stopped = true;
      cancelAnimationFrame(animationFrame);
      stream?.getTracks().forEach((track) => track.stop());
      if (cameraVideoRef.current) cameraVideoRef.current.srcObject = null;
      setPersonDetected(false);
    };
  }, [cameraActive, activeView]);

  const recognizeFrame = async (blob) => {
    const body = new FormData();
    body.append('frame', blob, 'face.jpg');
    const response = await fetch('/api/recognize-person', {
      method:'POST', headers:{ Authorization:`Bearer ${session.token}` }, body,
    });
    const result = await response.json().catch(() => ({}));
    if (response.status === 503) {
      // Graceful face-presence fallback when downloadable weights are missing.
      const fallback = await fetch('/api/detect-person', {
        method:'POST', headers:{Authorization:`Bearer ${session.token}`}, body:(()=>{const f = new FormData(); f.append('frame',blob,'fallback.jpg'); return f;})(),
      });
      if (fallback.ok) return {...await fallback.json(), enrolled_people:0, recognition_unavailable:result.detail || 'Recognition models unavailable'};
    }
    if (!response.ok) throw new Error(result.detail || `Recognition failed (${response.status})`);
    return result;
  };

  const applyIdentityResults = (result, isLive = false) => {
    const rawFaces = result.faces || [];
    const oneMatch = rawFaces.length === 1 && rawFaces[0].status === 'matched' ? rawFaces[0] : null;
    // A single webcam frame can be blurred or misclassified. Wait for three
    // consecutive results from the SAME enrolled person before naming them.
    let stableMatch = oneMatch;
    let matchingFrames = oneMatch ? 1 : 0;
    if (isLive) {
      const history = identityMatchHistoryRef.current;
      history.push(oneMatch?.person_id ?? null);
      if (history.length > 5) history.shift();
      matchingFrames = oneMatch ? [...history].reverse().findIndex(id => id !== oneMatch.person_id) : 0;
      if (oneMatch && matchingFrames === -1) matchingFrames = history.length;
      stableMatch = matchingFrames >= 3 ? oneMatch : null;
    } else {
      identityMatchHistoryRef.current = [];
    }

    const faces = isLive && oneMatch && !stableMatch
      ? rawFaces.map(face => ({...face, status: 'checking', name: null}))
      : rawFaces;
    setIdentityFaceDetected(result.face_detected);
    setCameraCheck('working');
    setIdentityFaceBoxes(faces);
    if (result.recognition_unavailable) {
      setIdentityStatus(`${faces.length ? 'A face is visible. ' : 'No face found. '}${result.recognition_unavailable}`);
    } else if (!rawFaces.length) {
      setIdentityStatus('No face detected. Face the camera, move closer, remove obstructions and improve lighting.');
      lastAnnouncedRef.current = null;
    } else if (oneMatch && !stableMatch) {
      setIdentityStatus(`Checking this face across camera frames (${matchingFrames}/3)… Hold the camera steady.`);
    } else if (stableMatch) {
      const person = stableMatch;
      const score = Number.isFinite(person.similarity) ? ` Similarity score ${person.similarity.toFixed(2)} (not a probability).` : '';
      const extra = person.quality_hint ? ` ${person.quality_hint}` : '';
      setIdentityStatus(`Possible match: ${person.name} — ${relationshipLabel(person.relationship)}. Verify with a caregiver if unsure.${score}${extra}`);
      if (speakNamesEnabledRef.current && lastAnnouncedRef.current !== person.person_id) {
        speak(`Possible match: ${person.name}. Please confirm with your caregiver.`);
        lastAnnouncedRef.current = person.person_id;
      }
    } else if (rawFaces.length > 1) {
      setIdentityStatus(`${rawFaces.length} faces detected. For a more reliable match, show one person at a time.`);
      lastAnnouncedRef.current = null;
    } else if (!result.enrolled_people) {
      setIdentityStatus('Face detected, but nobody has enrolled photos yet. Ask the caregiver to add 3–5 clear pictures per person.');
      lastAnnouncedRef.current = null;
    } else {
      const detected = rawFaces[0];
      const detail = detected.reason === 'ambiguous'
        ? 'This face resembles several saved profiles.'
        : detected.reason === 'low_quality'
          ? 'The camera image is too blurry, dark, bright, or small for reliable recognition.'
          : detected.reason === 'inconsistent_samples'
            ? 'The saved photos do not agree about this person. The caregiver should review the enrollment photos.'
            : detected.reason === 'low_similarity'
              ? 'The photo does not closely match an enrolled person.'
              : detected.reason === 'detection_only'
                ? 'A possible face is visible, but recognition landmarks are not clear enough.'
                : 'This person is not recognized.';
      const tip = detected.quality_hint ? ` ${detected.quality_hint}` : ' Try better lighting or a different photo.';
      setIdentityStatus(`${detail} Showing Unknown is safer than guessing a name.${tip}`);
      lastAnnouncedRef.current = null;
    }
  };

  useEffect(() => {
    if (!identityCameraActive || activeView !== 'home') {
      if (identityCameraActive) setIdentityCameraActive(false);
      return;
    }
    let stream;
    let stopped = false;
    let animationFrame = 0;
    let detecting = false;
    let lastAt = 0;
    identityMatchHistoryRef.current = [];

    const check = async (stamp) => {
      if (stopped) return;
      const video = identityVideoRef.current;
      if (!detecting && stamp - lastAt > 900 && video?.readyState >= 2 && video.videoWidth) {
        detecting = true;
        lastAt = stamp;
        try {
          const canvas = document.createElement('canvas');
          const scale = Math.min(1, 960 / Math.max(video.videoWidth, video.videoHeight));
          canvas.width = Math.round(video.videoWidth * scale);
          canvas.height = Math.round(video.videoHeight * scale);
          canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
          const blob = await new Promise((resolve, reject) => canvas.toBlob(
            file => file ? resolve(file) : reject(new Error('Camera frame could not be captured.')), 'image/jpeg', 0.9));
          const result = await recognizeFrame(blob);
          if (!stopped) applyIdentityResults(result, true);
        } catch (error) {
          if (!stopped) {
            setIdentityFaceBoxes([]);
            setIdentityStatus(error.message || 'Recognition is unavailable. Check that the API is running.');
          }
        } finally { detecting = false; }
      }
      if (!stopped) animationFrame = requestAnimationFrame(check);
    };

    async function start() {
      if (!navigator.mediaDevices?.getUserMedia) {
        setIdentityStatus('Camera unavailable. Open the app on localhost or HTTPS, or upload a photo.');
        setCameraCheck('error');
        setIdentityCameraActive(false);
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({audio:false, video:{facingMode:'user', width:{ideal:1280}, height:{ideal:720}}});
        if (stopped) { stream.getTracks().forEach(track => track.stop()); return; }
        const video = identityVideoRef.current;
        if (!video) { stream.getTracks().forEach(track=>track.stop()); return; }
        video.srcObject = stream;
        await video.play();
        if (!stopped) {
          setCameraCheck('working');
          setIdentityStatus(recognitionInfo.ready ? 'Camera connected. Looking for enrolled faces…' : 'Camera connected. Face presence works, but identity models need installation.');
          animationFrame = requestAnimationFrame(check);
        }
      } catch (error) {
        if (!stopped) {
          setIdentityStatus(error.name === 'NotAllowedError'
            ? 'Camera permission denied. Click the lock icon in the address bar to allow access, then retry.'
            : 'Could not start camera. Close other apps using it, or upload a photo instead.');
          setCameraCheck('error');
          setIdentityCameraActive(false);
        }
      }
    }
    start();
    return () => {
      stopped = true;
      cancelAnimationFrame(animationFrame);
      stream?.getTracks().forEach(track=>track.stop());
      identityMatchHistoryRef.current = [];
      if (identityVideoRef.current) identityVideoRef.current.srcObject = null;
    };
  }, [identityCameraActive, activeView, session?.token]);

  const detectPhotoIdentity = async (file) => {
    if (!file) return;
    setIdentityBusy(true);
    setIdentityReminderMessage('');
    setIdentityCameraActive(false);
    try {
      const optimized = await compressDetectionImage(file);
      if (identityPhotoUrlRef.current) URL.revokeObjectURL(identityPhotoUrlRef.current);
      identityPhotoUrlRef.current = URL.createObjectURL(optimized);
      setIdentityPhoto(identityPhotoUrlRef.current);
      setIdentityFaceBoxes([]);
      setIdentityStatus('Analyzing your photo locally…');
      const result = await recognizeFrame(optimized);
      applyIdentityResults(result);
    } catch (error) {
      setIdentityFaceDetected(false);
      setIdentityFaceBoxes([]);
      setIdentityStatus(error.message || 'Could not recognize this photo.');
    } finally { setIdentityBusy(false); }
  };

  const refreshRecognition = async () => {
    try {
      const data = await fetchJson('/api/recognition/status');
      setRecognitionInfo(data);
      return data;
    } catch (error) {
      setRecognitionInfo(info => ({...info, ready:false, message:error.message}));
      return null;
    }
  };

  const installModels = async () => {
    setSetupBusy(true);
    setSetupMessage('Downloading and checking official OpenCV models. Keep the app open during setup.');
    try {
      const result = await fetchJson('/api/recognition/install', {method:'POST'});
      setSetupMessage(result.ready ? 'AI models installed and ready. Now enroll a family face.' : result.message);
      await refreshRecognition();
    } catch (error) { setSetupMessage(error.message || 'Could not install recognition models.'); }
    finally { setSetupBusy(false); }
  };

  const enrollPhoto = async (personId, file) => {
    if (!file) return;
    if (!enrollConsent) {
      setProfileMessage('Confirm the person has given permission to use their photo for matching.');
      return;
    }
    setEnrollBusy(true);
    setProfileMessage('Adding an enrolled face sample…');
    try {
      const photo = await compressDetectionImage(file);
      const body = new FormData();
      body.append('frame', photo, 'enrollment.jpg');
      const response = await fetch(`/api/family-members/${personId}/enroll?consent=true`, {
        method:'POST', headers:{Authorization:`Bearer ${session.token}`}, body,
      });
      const data = await response.json().catch(()=>({}));
      if (!response.ok) throw new Error(data.detail || `Enrollment failed (${response.status})`);
      setProfileMessage(`${data.message}. ${data.samples} sample(s) enrolled. Recommended: 3–5 distinct photos in daylight (front, slight left, slight right).`);
      setEnrollTarget(null);
      await refreshRecognition();
    } catch (error) { setProfileMessage(error.message || 'Enrollment failed.'); }
    finally { setEnrollBusy(false); }
  };

  const deleteEnrollment = async (personId) => {
    if (!window.confirm('Remove the face samples for this person? Their profile will remain.')) return;
    try {
      await fetchJson(`/api/family-members/${personId}/enrollment`, {method:'DELETE'});
      setProfileMessage('Face samples removed.');
      await refreshRecognition();
    } catch (error) { setProfileMessage(error.message); }
  };


  const fetchJson = async (url, options = {}) => {
    const response = await fetch(url, {
      cache: 'no-store',
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${session?.token || ''}`,
        ...options.headers,
      },
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      if (response.status === 401) {
        sessionStorage.removeItem('remind_session');
        setSession(null);
      }
      throw new Error(typeof data.detail === 'string' ? data.detail : `Request failed (${response.status})`);
    }
    return response.json();
  };

  const refreshNotificationCount = async () => {
    if (!session?.token) return;
    try {
      const res = await fetch(`/api/caregiver/notifications`, {headers: { Authorization: `Bearer ${session.token}` }});
      if (res.ok) setNotificationCount((await res.json()).count);
    } catch { /* A temporary network interruption should not interrupt patient activities. */ }
  };
  useEffect(() => {
    if (!session?.token) { setNotificationCount(0); return; }
    refreshNotificationCount();
    const timer = setInterval(refreshNotificationCount, 20000);
    return () => clearInterval(timer);
  }, [session?.token]);

  const loadMonitoring = async (days = monitoringDays) => {
    if (!session?.token) return;
    setMonitoringBusy(true);
    setMonitoringError('');
    try { setMonitoring(await fetchJson(`/api/caregiver/monitoring?days=${days}`)); }
    catch (error) { setMonitoringError(error.message || 'Could not load monitoring activity.'); }
    finally { setMonitoringBusy(false); }
  };
  useEffect(() => {
    if (session?.token && activeView === 'dashboard') loadMonitoring(monitoringDays);
  }, [session?.token, activeView, monitoringDays]);
  const exportObjectHistory = async () => {
    try {
      const response = await fetch(`/api/caregiver/monitoring.csv?days=${monitoringDays}`, {headers:{Authorization:`Bearer ${session.token}`}});
      if (!response.ok) throw new Error(`Export failed (${response.status})`);
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a'); link.href=url; link.download='remind-object-requests.csv'; link.click();
      setTimeout(()=>URL.revokeObjectURL(url),1000);
    } catch (error) { setMonitoringError(error.message); }
  };
  const clearObjectHistory = async () => {
    if (!window.confirm('Delete recorded object requests for this account? Saved object locations will not be deleted.')) return;
    try { await fetchJson('/api/caregiver/object-lookups',{method:'DELETE'}); await loadMonitoring(); }
    catch (error) { setMonitoringError(error.message); }
  };
  const addCaregiverNote = async () => {
    if (!careNote.trim()) return;
    try { await fetchJson('/api/caregiver/notes',{method:'POST',body:JSON.stringify({text:careNote.trim()})}); setCareNote(''); await loadMonitoring(); }
    catch (error) { setMonitoringError(error.message); }
  };
  const deleteCaregiverNote = async id => {
    try { await fetchJson(`/api/caregiver/notes/${id}`,{method:'DELETE'}); await loadMonitoring(); }
    catch (error) { setMonitoringError(error.message); }
  };
  const saveIdentityReminder = async person => {
    if (!person?.person_id) return;
    try {
      const result = await fetchJson('/api/identity-reminder', {method:'POST', body:JSON.stringify({family_member_id:person.person_id})});
      setIdentityReminderMessage(result.message);
    } catch (error) { setIdentityReminderMessage(error.message || 'Could not save that reminder.'); }
  };
  const lookupObject = async name => {
    const value = name.trim();
    if (!value) return;
    setObjectLookupBusy(true); setObjectLookupResult(null);
    try {
      const result = await fetchJson('/api/object-lookup',{method:'POST',body:JSON.stringify({name:value})});
      setObjectLookupResult(result); setObjectLookupName(value);
      await refreshNotificationCount();
      if (activeView === 'dashboard') await loadMonitoring();
    } catch (error) { setObjectLookupResult({answer:error.message || 'Could not look up this object.'}); }
    finally { setObjectLookupBusy(false); }
  };
  const loadAnalytics = async (days = analyticsDays) => {
    if (!session?.token) return;
    setAnalyticsBusy(true);
    setAnalyticsError('');
    try { setAnalytics(await fetchJson(`/api/caregiver/analytics?days=${days}`)); }
    catch (error) { setAnalyticsError(error.message || 'Cannot load analytics.'); }
    finally { setAnalyticsBusy(false); }
  };
  useEffect(() => {
    if (session?.token && activeView === 'dashboard') loadAnalytics(analyticsDays);
  }, [session?.token, activeView, analyticsDays]);
  const exportAnalytics = async () => {
    try {
      const response = await fetch(`/api/caregiver/questions.csv?days=${analyticsDays}`, {headers:{Authorization:`Bearer ${session.token}`}});
      if (!response.ok) throw new Error('CSV download failed.');
      const objectUrl = URL.createObjectURL(await response.blob());
      const link = document.createElement('a');
      link.href = objectUrl; link.download = 'remind-question-history.csv'; link.click();
      setTimeout(()=>URL.revokeObjectURL(objectUrl), 1000);
    } catch (error) { setAnalyticsError(error.message); }
  };
  const clearAnalytics = async () => {
    if (!window.confirm('Permanently delete all saved patient questions for this account? This cannot be undone.')) return;
    try { await fetchJson('/api/caregiver/questions', {method:'DELETE'}); await loadAnalytics(); }
    catch (error) { setAnalyticsError(error.message); }
  };

  const withFormErrors = (handler) => async (event) => {
    setApiError('');
    try { await handler(event); }
    catch (error) { setApiError(error.message || 'Could not save the record.'); }
  };

  const loadAllData = async () => {
    try {
      const [home, peopleData, objectData, memoryData, scheduleData, reminderData, prefData, emergencyData, auditData] = await Promise.all([
        fetchJson('/api/home'),
        fetchJson('/api/family-members'),
        fetchJson('/api/objects'),
        fetchJson('/api/memories'),
        fetchJson('/api/schedule'),
        fetchJson('/api/reminders'),
        fetchJson('/api/preferences'),
        fetchJson('/api/emergency'),
        fetchJson('/api/audit'),
      ]);

      setHomeData(home);
      setPeople(peopleData);
      setObjects(objectData);
      setMemories(memoryData);
      setSchedule(scheduleData);
      setReminders(reminderData);
      setPreferences(prefData);
      setEmergencyContacts(emergencyData);
      setAuditLog(auditData);
    } catch (error) {
      setApiError(error.message || 'Could not load saved information.');
    }
  };

  useEffect(() => {
    if (session?.token) { loadAllData(); refreshRecognition(); }
  }, [session?.token]);

  const handleAction = (actionId) => {
    setActiveView(actionId === 'person' ? 'home' : actionId);
    if (actionId === 'person') requestAnimationFrame(() => document.getElementById('face-scanner')?.scrollIntoView({behavior:'smooth',block:'start'}));
    if (actionId === 'voice') {
      setActiveView('voice');
    }
  };

  const handlePersonSubmit = async (event) => {
    event.preventDefault();
    const form = event.target;
    const body = {
      name: form.elements.namedItem('name').value.trim(),
      relationship: form.elements.namedItem('relationship').value.trim(),
      description: form.elements.namedItem('description').value.trim(),
      photo_url: familyPhoto || '/images/default-person.jpg',
    };
    try {
      const newPerson = await fetchJson('/api/family-members', { method: 'POST', body: JSON.stringify(body) });
      let enrollmentStatus = 'Profile saved. Add a face sample with permission to enable recognition.';
      if (enrollConsent && familyPhoto) {
        try {
          const photo = await (await fetch(familyPhoto)).blob();
          const enrollment = new FormData();
          enrollment.append('frame', photo, 'profile.jpg');
          const reply = await fetch(`/api/family-members/${newPerson.id}/enroll?consent=true`, {
            method:'POST', headers:{Authorization:`Bearer ${session.token}`}, body:enrollment,
          });
          const result = await reply.json().catch(()=>({}));
          if (!reply.ok) throw new Error(result.detail || 'Enrollment failed.');
          enrollmentStatus = `Profile and face sample saved for ${newPerson.name}. Add more samples for better matching.`;
        } catch (error) { enrollmentStatus = `Profile saved, but face enrollment failed: ${error.message}`; }
      }
      form.reset();
      setFamilyPhoto('');
      setEnrollConsent(false);
      setProfileMessage(enrollmentStatus);
      await loadAllData();
      await refreshRecognition();
    } catch (error) {
      setProfileMessage(error.message || 'Could not save this family profile.');
    }
  };

  const handleFamilyPhoto = async (file) => {
    if (!file) return;
    try {
      setFamilyPhoto(await normalizePhoto(file));
      setProfileMessage('');
    } catch (error) {
      setProfileMessage(error.message);
    }
  };

  const captureFamilyPhoto = async () => {
    const video = cameraVideoRef.current;
    if (!video?.videoWidth) {
      setCameraMessage('Wait for the camera preview to start before capturing.');
      return;
    }
    const canvas = document.createElement('canvas');
    const scale = Math.min(1, 900 / Math.max(video.videoWidth, video.videoHeight));
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.82));
    if (!blob) {
      setCameraMessage('Could not capture the photo. Please try again.');
      return;
    }
    try {
      setFamilyPhoto(await normalizePhoto(new File([blob], 'camera-photo.jpg', { type: 'image/jpeg' })));
      setProfileMessage('');
    } catch (error) {
      setProfileMessage(error.message);
    }
  };

  const handleObjectSubmit = async (event) => {
    event.preventDefault();
    const form = event.target;
    const body = {
      name: form.elements.namedItem('name').value,
      category: form.elements.namedItem('category').value,
      last_location: form.elements.namedItem('last_location').value,
      notes: form.elements.namedItem('notes').value,
    };
    await fetchJson('/api/objects', { method: 'POST', body: JSON.stringify(body) });
    form.reset();
    await loadAllData();
  };

  const uploadMemoryFiles = async (memoryId, files) => {
    const selected = Array.from(files || []);
    for (const file of selected) {
      if (!['image/jpeg','image/png','image/webp','video/mp4','video/webm'].includes(file.type)) {
        throw new Error(`Unsupported file: ${file.name}. Choose JPEG, PNG, WebP, MP4 or WebM.`);
      }
      const maxSize = file.type.startsWith('video/') ? 40 * 1024 * 1024 : 8 * 1024 * 1024;
      if (file.size > maxSize) throw new Error(`${file.name} is too large. Maximum: ${file.type.startsWith('video/') ? '40 MB' : '8 MB'}.`);
      const body = new FormData();
      body.append('file', file);
      const response = await fetch(`/api/memories/${memoryId}/media`, {
        method: 'POST', headers: { Authorization: `Bearer ${session.token}` }, body,
      });
      if (!response.ok) {
        const result = await response.json().catch(() => ({}));
        throw new Error(result.detail || `Could not save ${file.name}`);
      }
    }
  };

  const handleExistingMemoryFiles = async (memoryId, files) => {
    setMemoryUploading(memoryId);
    setApiError('');
    try {
      await uploadMemoryFiles(memoryId, files);
      await loadAllData();
    } catch (error) { setApiError(error.message); }
    finally { setMemoryUploading(null); }
  };

  const handleDeleteMemoryMedia = async item => {
    if (!window.confirm(`Remove ${item.original_name} from this memory?`)) return;
    try {
      await fetchJson(`/api/memories/media/${item.id}`, { method: 'DELETE' });
      await loadAllData();
    } catch (error) { setApiError(error.message); }
  };

  const handleMemorySubmit = async (event) => {
    event.preventDefault();
    const form = event.target;
    const body = {
      title: form.elements.namedItem('title').value,
      caption: form.elements.namedItem('caption').value,
      description: form.elements.namedItem('description').value,
    };
    const selectedFiles = Array.from(form.elements.namedItem('media_files')?.files || []);
    const saved = await fetchJson('/api/memories', { method: 'POST', body: JSON.stringify(body) });
    try {
      if (selectedFiles.length) await uploadMemoryFiles(saved.id, selectedFiles);
    } catch (error) {
      setApiError(`Memory saved, but a media upload failed: ${error.message}. Use Add media to retry.`);
    }
    form.reset();
    await loadAllData();
  };

  const handleScheduleSubmit = async (event) => {
    event.preventDefault();
    const form = event.target;
    const body = {
      title: form.elements.namedItem('title').value,
      scheduled_for: form.elements.namedItem('scheduled_for').value,
      notes: form.elements.namedItem('notes').value,
    };
    await fetchJson('/api/schedule', { method: 'POST', body: JSON.stringify(body) });
    form.reset();
    await loadAllData();
  };

  const handleReminderSubmit = async (event) => {
    event.preventDefault();
    const form = event.target;
    const body = {
      title: form.elements.namedItem('title').value,
      reminder_time: form.elements.namedItem('reminder_time').value,
      notes: form.elements.namedItem('notes').value,
    };
    await fetchJson('/api/reminders', { method: 'POST', body: JSON.stringify(body) });
    form.reset();
    await loadAllData();
  };

  const handlePreferenceSubmit = async (event) => {
    event.preventDefault();
    const form = event.target;
    const body = {
      response_mode: form.elements.namedItem('response_mode').value,
      voice_first: form.elements.namedItem('voice_first').checked,
      detail_level: form.elements.namedItem('detail_level').value,
      reminder_format: form.elements.namedItem('reminder_format').value,
    };
    const updated = await fetchJson('/api/preferences', { method: 'POST', body: JSON.stringify(body) });
    setPreferences(updated);
    await loadAllData();
  };

  const handleEmergencySubmit = async (event) => {
    event.preventDefault();
    const form = event.target;
    const body = {
      name: form.elements.namedItem('name').value,
      phone: form.elements.namedItem('phone').value,
      relationship: form.elements.namedItem('relationship').value,
    };
    await fetchJson('/api/emergency', { method: 'POST', body: JSON.stringify(body) });
    form.reset();
    await loadAllData();
  };

  const handleDelete = async (url, description) => {
    if (!window.confirm(`Delete ${description}? This cannot be undone.`)) return;
    setDeleteMessage('');
    try {
      await fetchJson(url, { method: 'DELETE' });
      await loadAllData();
      setDeleteMessage(`${description} deleted.`);
    } catch (error) {
      setDeleteMessage(error.message || `Could not delete ${description}.`);
    }
  };

  const handleEditSubmit = async (event) => {
    event.preventDefault();
    const { type, record } = editingRecord;
    const form = event.target;
    const value = (name) => form.elements.namedItem(name)?.value ?? '';
    const payloadBuilders = {
      person: () => ({
        name: value('name').trim(),
        relationship: value('relationship').trim(),
        description: value('description').trim(),
        photo_url: record.photo_url,
        approved: record.approved,
      }),
      object: () => ({
        name: value('name').trim(),
        category: value('category'),
        last_location: value('last_location').trim(),
        notes: value('notes').trim(),
        last_seen_at: record.last_seen_at,
        photo_url: record.photo_url,
      }),
      memory: () => ({
        title: value('title').trim(),
        caption: value('caption').trim(),
        description: value('description').trim(),
        person_id: record.person_id,
        photo_url: record.photo_url,
        recorded_on: record.recorded_on,
        voice_note: record.voice_note,
        approved: record.approved,
      }),
      schedule: () => ({
        title: value('title').trim(),
        scheduled_for: value('scheduled_for'),
        notes: value('notes').trim(),
        approved: record.approved,
      }),
      reminder: () => ({
        title: value('title').trim(),
        reminder_time: value('reminder_time'),
        notes: value('notes').trim(),
        acknowledged: record.acknowledged,
      }),
      emergency: () => ({
        name: value('name').trim(),
        phone: value('phone').trim(),
        relationship: value('relationship').trim(),
        notification_enabled: record.notification_enabled,
      }),
    };
    const endpoints = {
      person: 'family-members',
      object: 'objects',
      memory: 'memories',
      schedule: 'schedule',
      reminder: 'reminders',
      emergency: 'emergency',
    };

    setEditMessage('');
    try {
      await fetchJson(`/api/${endpoints[type]}/${record.id}`, {
        method: 'PUT',
        body: JSON.stringify(payloadBuilders[type]()),
      });
      await loadAllData();
      setEditingRecord(null);
      setDeleteMessage('Record updated.');
    } catch (error) {
      setEditMessage(error.message || 'Could not update this record.');
    }
  };

  const datetimeLocalValue = (value) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
    return date.toISOString().slice(0, 16);
  };

  const handleAsk = async () => {
    if (!question.trim()) return;
    setLoading(true);
    try {
      const result = await fetchJson('/api/question', {
        method: 'POST',
        body: JSON.stringify({ question, source: questionSource }),
      });
      setAssistantAnswer(`${result.answer} Evidence: ${result.evidence.join(' ') || 'Database records only.'}`);
      setQuestion('');
      setQuestionSource('typed');
      await refreshNotificationCount();
      if (activeView === 'dashboard') { loadAnalytics(); loadMonitoring(); }
    } catch (error) {
      setAssistantAnswer('I could not reach the memory retrieval service right now. Please try again soon.');
    } finally {
      setLoading(false);
    }
  };

  const speak = (text) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.88;
      utterance.lang = voiceLanguage;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
    }
  };

  const startListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setAssistantAnswer('Speech recognition is not supported in this browser. You can still type your question.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = voiceLanguage;
    recognition.onresult = (event) => {
      const spoken = event.results[0][0].transcript;
      setQuestion(spoken);
      setQuestionSource('voice');
      setAssistantAnswer(`Heard: "${spoken}"`);
    };
    recognition.onerror = () => {
      setAssistantAnswer('Speech recognition could not understand your request. Please try again or type your question.');
    };
    recognition.onend = () => setIsListening(false);

    recognition.start();
    setIsListening(true);
    recognitionRef.current = recognition;
  };

  const statusCards = useMemo(() => [
    { label: 'Next activity', value: homeData.next_activity || 'No scheduled activity', icon: CalendarDays },
    { label: 'Upcoming reminders', value: homeData.upcoming_reminders?.[0] || 'No reminders', icon: Bell },
    { label: 'Response mode', value: homeData.preferences?.response_mode || 'text', icon: Sparkles },
  ], [homeData]);

  if (!session) {
    return (
      <div className="login-screen min-h-screen p-5 lg:p-12">
        <div className="mx-auto flex min-h-[88vh] max-w-6xl items-center gap-12">
          <div className="hidden flex-1 text-white lg:block">
            <div className="mb-9 inline-flex items-center gap-3 rounded-full border border-white/20 px-4 py-2 text-sm text-emerald-100"><Heart className="h-4 w-4" /> Built with care, powered by memory</div>
            <h1 className="mb-6 max-w-lg text-6xl font-extrabold leading-[1.04] tracking-tight">Every face.<br />Every memory.<br /><span className="text-emerald-300">Every moment.</span></h1>
            <p className="max-w-lg text-lg leading-relaxed text-slate-300">A thoughtful companion to help families reconnect, remember, and feel supported through every day.</p>
            <div className="mt-12 flex gap-5 text-sm text-slate-200"><span className="inline-flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-emerald-300" /> Consent-based</span><span className="inline-flex items-center gap-2"><Fingerprint className="h-5 w-5 text-emerald-300" /> On-device server matching</span></div>
          </div>
          <div className="w-full max-w-md rounded-[2rem] border border-white/15 bg-white p-8 shadow-2xl lg:p-10">
            <div className="mb-6 flex items-center gap-3"><div className="brand-icon"><Heart size={25}/></div><div><div className="text-2xl font-extrabold tracking-tight text-slate-900">ReMind <span className="text-emerald-600">AI</span></div><div className="text-xs font-medium text-slate-500">YOUR MEMORY COMPANION</div></div></div>
            <h2 className="text-2xl font-bold tracking-tight">Welcome back</h2>
            <p className="mb-6 mt-1 text-sm text-slate-500">Sign in to access your personal space.</p>
            <form onSubmit={(event) => {event.preventDefault();signIn(event.target.elements.namedItem('email').value.trim(),event.target.elements.namedItem('password').value);}} className="space-y-4">
              <label className="block text-sm font-semibold text-slate-700">Email address<input className="mt-2 w-full" name="email" type="email" autoComplete="username" placeholder="you@example.com" required /></label>
              <label className="block text-sm font-semibold text-slate-700">Password<input className="mt-2 w-full" name="password" type="password" autoComplete="current-password" placeholder="Enter your password" required /></label>
              <button disabled={loginBusy} type="submit" className="btn-primary w-full py-3.5">{loginBusy ? 'Signing in…' : 'Sign in'} <ArrowRight size={18}/></button>
            </form>
            <div className="my-6 flex items-center gap-3 text-xs font-bold tracking-widest text-slate-400"><div className="h-px flex-1 bg-slate-200"/> HACKATHON DEMO <div className="h-px flex-1 bg-slate-200"/></div>
            <button disabled={loginBusy} onClick={startDemo} className="btn-soft w-full py-3.5"><Sparkles size={18}/> Try the interactive demo</button>
            {loginError && <p role="alert" className="mt-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{loginError}</p>}
            <p className="mt-6 text-xs leading-relaxed text-slate-500">Runs locally for demonstration. Use synthetic demo data, not real patient records, in public presentations.</p>
          </div>
        </div>
      </div>
    );
  }

  const orderedAgenda = [
    ...schedule.map(entry => ({ ...entry, kind: 'schedule', time: entry.scheduled_for })),
    ...reminders.map(entry => ({ ...entry, kind: 'reminder', time: entry.reminder_time })),
  ].sort((left, right) => left.time.localeCompare(right.time) || left.title.localeCompare(right.title));

  const primaryMatch = identityFaceBoxes.length === 1 && identityFaceBoxes[0]?.status === 'matched' ? identityFaceBoxes[0] : null;
  return (
    <div className="app-background min-h-screen text-slate-800">
      <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 md:px-7">
          <button onClick={() => handleAction('home')} className="flex items-center gap-3 text-left" aria-label="ReMind AI Home">
            <div className="brand-icon"><Heart className="h-6 w-6" /></div>
            <span><span className="block text-xl font-extrabold tracking-tight text-slate-900">ReMind <span className="text-emerald-600">AI</span></span><span className="block text-[10px] font-semibold uppercase tracking-[.17em] text-slate-400">Here for your moments</span></span>
          </button>
          <nav className="hidden items-center gap-2 text-sm font-semibold md:flex" aria-label="Main navigation">
            <button onClick={()=>handleAction('home')} className={`nav-pill ${activeView==='home'?'active':''}`}><Home size={17}/> Home</button>
            <button onClick={()=>handleAction('person')} className="nav-pill"><ScanFace size={17}/> Face recognition</button>
            <button onClick={()=>handleAction('dashboard')} className={`nav-pill ${activeView==='dashboard'?'active':''}`}><UsersRound size={17}/> Caregiver Studio {notificationCount > 0 && <span aria-label={`${notificationCount} requests`} className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-extrabold text-amber-900">{notificationCount}</span>}</button>
          </nav>
          <div className="hidden items-center gap-3 md:flex"><span className="rounded-full bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800"><span className="mr-2 inline-block h-2 w-2 rounded-full bg-emerald-500"/> Local session</span><button onClick={signOut} className="btn-outline text-sm">Sign out</button></div>
          <button className="rounded-xl border border-slate-200 p-2 md:hidden" aria-label="Toggle menu" onClick={()=>setMobileMenu(v=>!v)}>{mobileMenu?<X size={22}/>:<Menu size={22}/>}</button>
        </div>
        {mobileMenu && <div className="grid gap-1 border-t border-slate-200 bg-white px-4 py-3 md:hidden">{[['home','Home'],['person','Face recognition'],['dashboard',`Caregiver Studio${notificationCount ? ` (${notificationCount})` : ''}`],['help','Get help']].map(([id,label])=><button key={id} className="rounded-xl p-3 text-left text-sm font-semibold hover:bg-emerald-50" onClick={()=>{handleAction(id);setMobileMenu(false)}}>{label}</button>)}<button className="rounded-xl p-3 text-left text-sm text-rose-600" onClick={signOut}>Sign out</button></div>}
      </header>
      <main className="mx-auto max-w-7xl px-4 pb-16 pt-7 md:px-7">
        {apiError && <div role="alert" className="mb-5 flex items-center justify-between gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"><span>{apiError}</span><button type="button" onClick={() => setApiError('')}>Dismiss</button></div>}

        {activeView === 'home' && (
          <>
            <section className="hero-panel mb-7 grid items-center gap-8 overflow-hidden rounded-[2rem] p-7 text-white md:grid-cols-[1.45fr_1fr] md:p-10">
              <div className="relative z-10">
                <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-emerald-300/30 bg-white/10 px-3 py-2 text-xs font-bold uppercase tracking-[.14em] text-emerald-100"><Sparkles size={15}/> YOUR EVERYDAY COMPANION</div>
                <h1 className="max-w-xl text-3xl font-extrabold leading-tight tracking-tight sm:text-4xl md:text-5xl">Good to see you, <span className="text-emerald-300">{session.user?.name?.split(' ')[0] || 'friend'}.</span></h1>
                <p className="mt-4 max-w-md text-base leading-relaxed text-slate-200">People, places, and little moments matter. ReMind helps keep them close.</p>
                <div className="mt-7 flex flex-wrap gap-3"><button className="btn-primary !bg-emerald-400 !text-slate-950 hover:!bg-emerald-300" onClick={()=>handleAction('person')}><ScanFace size={19}/> Recognize a face</button><button className="btn-outline !border-white/25 !bg-white/10 !text-white" onClick={()=>handleAction('dashboard')}><UsersRound size={18}/> Caregiver Studio</button></div>
              </div>
              <div className="hero-today relative z-10 rounded-3xl border border-white/20 p-6 backdrop-blur">
                <div className="flex items-center gap-2 text-sm font-bold text-emerald-200"><CalendarDays size={18}/> TODAY AT A GLANCE</div>
                <div className="mt-5 text-sm text-slate-300">Coming up next</div>
                <div className="mt-1 text-xl font-bold text-white">{homeData.next_upcoming?.title || 'Nothing scheduled yet'}</div>
                <div className="mt-1 text-xs text-emerald-100">{homeData.next_upcoming ? new Date(homeData.next_upcoming.at).toLocaleString() : ''}</div>
                <div className="mt-5 border-t border-white/20 pt-4 text-sm text-slate-300">Upcoming · earliest first</div>
                <div className="mt-2 max-h-36 space-y-2 overflow-y-auto">
                  {(homeData.upcoming_items || []).slice(0, 4).map((item, index) => <div key={`${item.kind}-${item.at}-${index}`} className="flex items-start justify-between gap-3 text-sm">
                    <span className="min-w-0 break-words font-semibold text-white">{item.title}</span>
                    <span className="shrink-0 text-xs text-emerald-100">{new Date(item.at).toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})}</span>
                  </div>)}
                  {!homeData.upcoming_items?.length && <span className="text-sm text-white">You're all caught up.</span>}
                </div>
                <div className="mt-6 inline-flex items-center gap-2 rounded-full bg-emerald-300/20 px-3 py-2 text-xs font-semibold text-emerald-100"><ShieldCheck size={15}/> Designed with care</div>
              </div>
            </section>

            <PatientDaily token={session.token}/>
            <div className="mb-7 rounded-[24px] border border-emerald-200 bg-white p-5 shadow-sm md:flex md:items-center md:justify-between md:gap-6"><div className="flex items-start gap-3"><div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-800"><Heart size={24}/></div><div><h2 className="text-lg font-extrabold text-slate-900">You're in the right place.</h2><p className="mt-1 text-sm text-slate-600">Need help remembering someone? Use the camera. Need a familiar answer? Ask ReMind. Want to update family photos? Open Caregiver Studio.</p></div></div><button className="btn-soft mt-4 shrink-0 md:mt-0" onClick={()=>handleAction('person')}><ScanFace size={18}/> Start with a face</button></div>
            <div className="mb-4 flex flex-wrap items-end justify-between gap-2"><div><p className="eyebrow">QUICK ACTIONS</p><h2 className="section-heading">What would you like to do?</h2></div><p className="text-sm text-slate-500">Simple support, one tap away</p></div>
            <section className="mb-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {ACTIONS.map(({ id, title, subtitle, icon: Icon }, i) => (
                <button key={id} onClick={()=>handleAction(id)} className="action-tile group flex items-center gap-4 rounded-2xl p-5 text-left">
                  <span className={`action-icon action-tone-${i}`}><Icon className="h-6 w-6"/></span>
                  <span className="min-w-0 flex-1"><span className="block text-base font-extrabold tracking-tight text-slate-900">{title}</span><span className="mt-1 block text-xs text-slate-500">{subtitle}</span></span>
                  <ArrowRight className="h-4 w-4 flex-shrink-0 text-slate-400 transition-transform group-hover:translate-x-1"/>
                </button>
              ))}
            </section>

            <section id="face-scanner" className="scanner-panel scroll-mt-28 overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-6 py-5 md:px-8">
                <div><p className="eyebrow"><ScanFace className="inline h-4 w-4"/> FACE RECOGNITION</p><h2 className="section-heading">Who is this person?</h2><p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-500">Recognize loved ones from photos they agreed to enroll. Unknown people stay unknown. For identification, enroll a real photo of each consenting person first.</p></div>
                <span className={`rounded-full px-3 py-2 text-xs font-bold ${recognitionInfo.ready?'bg-emerald-50 text-emerald-700':'bg-amber-50 text-amber-800'}`}><span className={`mr-2 inline-block h-2 w-2 rounded-full ${recognitionInfo.ready?'bg-emerald-500':'bg-amber-500'}`}/>{recognitionInfo.ready?'AI models ready':'Setup needed'}</span>
              </div>
              <div className="mx-5 mt-5 grid gap-2 sm:grid-cols-3 lg:mx-8">
                <div className={`setup-step ${recognitionInfo.ready?'done':'attention'}`}><span className="step-count">1</span><div><strong>AI models</strong><small>{recognitionInfo.ready?'Installed and ready':'Installation required'}</small></div></div>
                <div className={`setup-step ${recognitionInfo.enrolled_people?'done':'attention'}`}><span className="step-count">2</span><div><strong>Family photos</strong><small>{recognitionInfo.enrolled_people?`${recognitionInfo.enrolled_people} person(s) enrolled`:'Enroll a person with permission'}</small></div></div>
                <div className={`setup-step ${cameraCheck==='working'?'done':''}`}><span className="step-count">3</span><div><strong>Camera</strong><small>{cameraCheck==='working'?'Connected':'Start or upload a photo'}</small></div></div>
              </div>
              {!recognitionInfo.ready && <div className="mx-5 mt-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 lg:mx-8"><div><strong>Face naming is not ready yet.</strong><p>Install the YuNet + SFace models once, then enroll someone. Face detection alone cannot tell who a person is.</p></div><button type="button" className="btn-primary" onClick={installModels} disabled={setupBusy}>{setupBusy?'Installing…':'Install AI models'}</button></div>}
              {setupMessage && <p className="mx-5 mt-3 rounded-xl bg-slate-50 p-3 text-sm text-slate-600 lg:mx-8" role="status">{setupMessage}</p>}
              <div className="grid gap-7 p-5 lg:grid-cols-[1.2fr_.8fr] lg:p-8">
                <div className="space-y-4">
                  <div className="camera-stage relative flex min-h-[270px] items-center justify-center overflow-hidden rounded-3xl bg-slate-950">
                    {identityCameraActive || identityPhoto ? (
                      <div className="relative inline-flex max-h-[420px] max-w-full items-center justify-center overflow-hidden">
                        {identityCameraActive ? <video ref={identityVideoRef} autoPlay muted playsInline aria-label="Live face recognition camera" className="block max-h-[420px] max-w-full"/> : <img src={identityPhoto} alt="Selected photo for recognition" className="block max-h-[420px] max-w-full"/>}
                        {identityFaceBoxes.map((face, index) => (
                          <div key={index} className={`face-box absolute border-[3px] ${face.status === 'matched' ? 'border-emerald-400' : face.status === 'checking' ? 'border-sky-400' : 'border-amber-400'} rounded-2xl`} style={{left:`${face.x*100}%`,top:`${face.y*100}%`,width:`${face.width*100}%`,height:`${face.height*100}%`}}>
                            <span className={`absolute -top-7 left-0 whitespace-nowrap rounded-lg px-2 py-1 text-xs font-bold text-slate-950 ${face.status==='matched'?'bg-emerald-400':face.status==='checking'?'bg-sky-300':'bg-amber-300'}`}>{face.status==='matched'?`Possible: ${face.name}`:face.status==='checking'?'Checking…':'Unknown face'}</span>
                          </div>
                        ))}
                      </div>
                    ) : <div className="p-10 text-center"><div className="camera-emblem mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-3xl"><ScanFace size={38}/></div><p className="text-lg font-bold text-white">Ready when you are</p><p className="mt-2 max-w-xs text-sm text-slate-400">Turn on your camera or upload a photo to recognize someone you know.</p></div>}
                    {identityCameraActive && <div className="absolute right-4 top-4 inline-flex items-center gap-2 rounded-full bg-slate-950/65 px-3 py-2 text-xs font-bold text-white"><span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400"/> LIVE</div>}
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <button type="button" className={`btn-primary flex-1 sm:flex-none ${identityCameraActive?'!bg-rose-600 hover:!bg-rose-700':''}`} onClick={()=>{setIdentityCameraActive(v=>!v); setCameraCheck('idle'); setIdentityPhoto(''); setIdentityFaceBoxes([]); setIdentityStatus('');setIdentityReminderMessage('');lastAnnouncedRef.current=null;}}>
                      {identityCameraActive?<CameraOff size={19}/>:<Camera size={19}/>} {identityCameraActive?'Stop camera':'Start live camera'}
                    </button>
                    <label className="btn-outline flex-1 cursor-pointer sm:flex-none"><Upload size={19}/> {identityBusy?'Analyzing…':'Upload a photo'}<input type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" disabled={identityBusy} onChange={event=>{detectPhotoIdentity(event.target.files?.[0]);event.target.value='';}}/></label>
                  </div>
                  <label className="inline-flex items-center gap-2 rounded-2xl bg-slate-100 px-4 py-3 text-sm font-semibold text-slate-700"><input type="checkbox" checked={readNamesAloud} onChange={e=>setReadNamesAloud(e.target.checked)}/> Read recognized names aloud</label>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500"><span>Voice language:</span><select className="!w-auto !py-1.5 !text-sm" value={voiceLanguage} onChange={e=>setVoiceLanguage(e.target.value)}><option value="en-IN">English</option><option value="hi-IN">Hindi</option><option value="ml-IN">Malayalam</option></select><span>Availability depends on your browser.</span></div>
                  <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-slate-700">
                    <div className="font-bold text-slate-900">For better face recognition</div>
                    <p className="mt-1">Keep one face centered, at eye level, ideally at least 120 pixels wide in the camera image. Face a window or soft light, avoid strong backlighting, and hold still while the recognition label is checked across three frames.</p>
                    <p className="mt-2 text-xs text-slate-600">Caregivers: enroll 3–5 different consented photos per person (front, slightly left and right), not copies of the same photo. If recognition is uncertain, the app shows Unknown rather than guessing. Facial matching is not reliable enough for medical, safety, or login decisions.</p>
                    <p className="mt-2">Caregiver: enroll 3–5 different real photos per person under <strong>Caregiver Studio → Family Profiles</strong> (not repeated copies). A sample count of zero means this person cannot be recognized.</p>
                    <p className="mt-2">Live mode waits for <strong>three consistent camera frames</strong> before naming someone. A green box is only a possible match; verify identities with a caregiver.</p>
                  </div>
                  {identityStatus && <div role="status" className={`rounded-2xl border p-4 text-sm leading-relaxed ${primaryMatch?'border-emerald-200 bg-emerald-50 text-emerald-900':'border-slate-200 bg-slate-50 text-slate-700'}`}>{primaryMatch?<CheckCircle2 className="mr-2 inline h-5 w-5 text-emerald-700"/>:<AlertCircle className="mr-2 inline h-5 w-5 text-slate-500"/>}{identityStatus}</div>}
                </div>
                <aside className="flex flex-col gap-4">
                  {primaryMatch ? (
                    <div className="matched-card rounded-3xl border border-emerald-200 bg-emerald-50 p-6">
                      <div className="mb-3 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-800"><CheckCircle2 size={17}/> Possible match</div>
                      <h3 className="text-3xl font-extrabold tracking-tight text-slate-900">{primaryMatch.name}</h3>
                      <p className="mt-1 text-lg font-semibold text-emerald-800">{relationshipLabel(primaryMatch.relationship)}</p>
                      <p className="mt-4 text-sm text-slate-600">Matched to an enrolled family profile. Similarity score: {primaryMatch.similarity?.toFixed(2)} (not a probability). Please confirm when in doubt.</p>
                      <button type="button" className="btn-outline mt-5" onClick={()=>speak(`This looks like ${primaryMatch.name}. Your saved profile says ${relationshipLabel(primaryMatch.relationship)}.`)}><Volume2 size={18}/> Read aloud</button>
                      <button type="button" className="mt-3 block rounded-xl bg-emerald-700 px-4 py-2.5 text-sm font-bold text-white" onClick={()=>saveIdentityReminder(primaryMatch)}><CheckCircle2 size={16} className="mr-1 inline"/> Save this profile reminder</button>
                      {identityReminderMessage && <p role="status" className="mt-2 text-xs text-emerald-900">{identityReminderMessage}</p>}
                    </div>
                  ) : <div className="rounded-3xl bg-emerald-50/80 p-5"><p className="text-xs font-bold uppercase tracking-wider text-emerald-800">RECOGNITION STATUS</p><p className="mt-2 text-2xl font-extrabold text-slate-900">{recognitionInfo.enrolled_people || 0} <span className="text-base font-semibold text-slate-500">people enrolled</span></p><p className="mt-3 text-sm leading-relaxed text-slate-600">{recognitionInfo.message}</p>{!recognitionInfo.ready && <button type="button" disabled={setupBusy} onClick={installModels} className="btn-primary mt-4 w-full"><Sparkles size={17}/>{setupBusy?'Installing AI models…':'Install AI models'}</button>}{setupMessage && <p role="status" className="mt-3 text-xs leading-relaxed text-slate-700">{setupMessage}</p>}
                      <button onClick={refreshRecognition} type="button" className="mt-3 inline-flex items-center gap-2 text-xs font-bold text-emerald-800"><RefreshCw size={14}/> Refresh status</button></div>}
                  <div className="rounded-3xl border border-slate-200 p-5"><h3 className="mb-4 flex items-center gap-2 font-extrabold"><ShieldCheck size={19} className="text-emerald-600"/> How it works</h3><ol className="space-y-4 text-sm text-slate-600"><li className="flex gap-3"><span className="step-dot">1</span><span>Install the two recognition models (one-time setup).</span></li><li className="flex gap-3"><span className="step-dot">2</span><span>Add a person and their photos with permission in Caregiver Studio.</span></li><li className="flex gap-3"><span className="step-dot">3</span><span>Use the camera here to match against enrolled profiles.</span></li></ol><button onClick={()=>handleAction('dashboard')} className="btn-soft mt-6 w-full"><UsersRound size={17}/> Manage family faces <ArrowRight size={16}/></button></div>
                  <p className="px-1 text-xs leading-relaxed text-slate-500">Images are processed by the local backend; scan photos aren't saved. Matching can be wrong in difficult lighting. Do not use as medical or security verification.</p>
                </aside>
              </div>
            </section>

            <section className="mt-8 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
              <div className="panel rounded-3xl p-5">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-xl font-semibold">Talk to ReMind</h2>
                  <button onClick={() => speak(assistantAnswer)} className="rounded-full bg-sky-100 p-2 text-sky-700"><Volume2 className="h-5 w-5" /></button>
                </div>
                <div className="space-y-3">
                  <div className="flex flex-wrap gap-2" aria-label="Suggested questions">{['Who is my daughter?', 'Where is my pen?', 'Where are my keys?', 'What is my next reminder?'].map(example=><button key={example} type="button" className="rounded-full border border-sky-200 bg-sky-50 px-3 py-2 text-xs font-bold text-sky-800 hover:bg-sky-100" onClick={()=>{setQuestion(example);setQuestionSource('quick');}}>{example}</button>)}</div>
                  <textarea value={question} onChange={(e) => {setQuestion(e.target.value);setQuestionSource('typed');}} rows="3" placeholder="Ask: Who is my daughter?" className="w-full" />
                  <div className="flex gap-3">
                    <button onClick={handleAsk} className="rounded-full bg-sky-600 px-4 py-3 font-medium text-white shadow-lg shadow-sky-200">{loading ? 'Thinking...' : 'Ask ReMind'}</button>
                    <button onClick={startListening} className={`rounded-full px-4 py-3 font-medium ${isListening ? 'bg-rose-500 text-white' : 'bg-slate-100 text-slate-700'}`}>
                      <span className="inline-flex items-center gap-2"><Mic className="h-4 w-4" />{isListening ? 'Listening...' : 'Voice Input'}</span>
                    </button>
                  </div>
                </div>
                <div className="mt-4 rounded-2xl bg-sky-50 p-4 text-sm text-slate-700">
                  <div className="mb-2 flex items-center gap-2 font-semibold text-sky-700"><Bot className="h-4 w-4" /> ReMind response</div>
                  {assistantAnswer}
                </div>
              </div>

              <div className="panel rounded-3xl p-5">
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="text-xl font-semibold">Safety</h2>
                  <div className="rounded-full bg-rose-100 p-2 text-rose-700"><ShieldAlert className="h-5 w-5" /></div>
                </div>
                <button onClick={() => setActiveView('help')} className="mb-4 w-full rounded-2xl bg-gradient-to-r from-rose-500 to-orange-400 px-4 py-4 text-lg font-bold text-white shadow-lg shadow-rose-200">
                  SOS - Get Help
                </button>
                <div className="space-y-3 text-sm">
                  {emergencyContacts.length ? emergencyContacts.map((contact) => (
                    <div key={contact.id} className="rounded-2xl bg-slate-50 p-3">
                      <div className="font-semibold">{contact.name}</div>
                      <div className="text-slate-600">{contact.relationship}</div>
                      <div className="mt-1 flex items-center gap-2 text-sky-700"><Phone className="h-4 w-4" /> {contact.phone}</div>
                    </div>
                  )) : <div className="rounded-2xl bg-slate-50 p-3 text-slate-600">No emergency contacts added yet.</div>}
                </div>
              </div>
            </section>
          </>
        )}

        {activeView === 'dashboard' && (
          <section className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-extrabold tracking-tight">Caregiver Studio <span className="text-emerald-600">· manage & support</span></h2>
              <button onClick={() => setActiveView('home')} className="rounded-full border border-slate-200 bg-white px-4 py-2">Back to home</button>
            </div>
            {deleteMessage && <div className="rounded-xl bg-sky-50 p-3 text-sm text-sky-800" role="status">{deleteMessage}</div>}
            <CaregiverWorkspace token={session.token} onNotificationChange={setNotificationCount}
              onRecordChanged={async()=>{await loadAllData(); await refreshNotificationCount();}} />
            <PatientActivityMonitor data={monitoring} busy={monitoringBusy} error={monitoringError}
              days={monitoringDays} setDays={setMonitoringDays} onReload={()=>loadMonitoring()}
              onExport={exportObjectHistory} onClear={clearObjectHistory}
              noteText={careNote} setNoteText={setCareNote} onAddNote={addCaregiverNote} onDeleteNote={deleteCaregiverNote}/>
            <CareInsights analytics={analytics} busy={analyticsBusy} error={analyticsError}
              days={analyticsDays} setDays={setAnalyticsDays} onReload={()=>loadAnalytics()}
              onExport={exportAnalytics} onClear={clearAnalytics}/>


            <div className="grid gap-6 xl:grid-cols-[1.2fr_1fr]">
              <div className="space-y-6">
                <div className="panel rounded-3xl p-5">
                  <div className="mb-5"><p className="eyebrow">CAREGIVER STUDIO</p><h3 className="text-xl font-extrabold">Loved ones & face enrollment</h3><p className="mt-2 text-sm text-slate-500">Add people and enroll 2–3 clear photos of each person. Faces are matched only to approved profiles.</p></div>
                  {!recognitionInfo.ready && <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-relaxed text-amber-900"><AlertCircle className="mr-2 inline h-4 w-4"/><strong>One-time AI setup:</strong> <button type="button" className="font-bold underline" disabled={setupBusy} onClick={installModels}>{setupBusy?'Installing models…':'Install AI models'}</button> here, or run <code>py scripts\download_models.py</code> from the backend folder in CMD. Detection still works without the models. {setupMessage && <span className="mt-2 block">{setupMessage}</span>}</div>}
                  <div className="mb-3 inline-flex items-center gap-2 rounded-xl bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700">{recognitionInfo.enrolled_people || 0} enrolled profile(s) <button type="button" onClick={refreshRecognition} title="Refresh recognition status" className="ml-2 text-emerald-700"><RefreshCw size={15}/></button></div>
                  <form onSubmit={handlePersonSubmit} className="grid gap-3">
                    <input name="name" placeholder="Family member name" required />
                    <input name="relationship" placeholder="Relationship" required />
                    <textarea name="description" placeholder="Approved description" rows="3" />
                    <label className="flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 font-medium text-sky-700">
                      <Upload className="h-5 w-5" />
                      Upload a photo
                      <input
                        type="file"
                        accept="image/*"
                        className="sr-only"
                        onChange={(event) => handleFamilyPhoto(event.target.files?.[0])}
                      />
                    </label>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setCameraMessage('');
                          setCameraActive((active) => !active);
                        }}
                        className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 font-medium text-slate-700"
                      >
                        {cameraActive ? <CameraOff className="h-5 w-5" /> : <Camera className="h-5 w-5" />}
                        {cameraActive ? 'Stop camera' : 'Use camera'}
                      </button>
                      {cameraActive && (
                        <button type="button" onClick={captureFamilyPhoto} className="rounded-xl bg-teal-600 px-4 py-3 font-medium text-white">
                          Capture photo
                        </button>
                      )}
                    </div>
                    {cameraActive && (
                      <div className="space-y-2">
                        <video ref={cameraVideoRef} autoPlay muted playsInline className="max-h-72 w-full rounded-2xl bg-slate-900 object-cover" />
                        <div className={`rounded-xl p-3 text-sm ${personDetected ? 'bg-teal-50 text-teal-800' : 'bg-slate-50 text-slate-600'}`} aria-live="polite">
                          {cameraMessage || 'Starting camera…'}
                        </div>
                      </div>
                    )}
                    {!cameraActive && cameraMessage && (
                      <div className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800" role="status">{cameraMessage}</div>
                    )}
                    {familyPhoto && (
                      <div className="flex items-center gap-3 rounded-2xl bg-slate-50 p-3">
                        <img src={familyPhoto} alt="Selected family member" className="h-16 w-16 rounded-xl object-cover" />
                        <span className="text-sm text-slate-600">Photo ready to save</span>
                        <button type="button" onClick={() => setFamilyPhoto('')} className="ml-auto text-sm text-rose-700">Remove</button>
                      </div>
                    )}
                    <label className="flex cursor-pointer items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-relaxed text-slate-700"><input className="mt-1" type="checkbox" checked={enrollConsent} onChange={event=>setEnrollConsent(event.target.checked)}/><span>I have this person's permission to use their photo for local face recognition. When checked, saving a profile with a photo also enrolls that image.</span></label>
                    {profileMessage && <div className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-900" role="status">{profileMessage}</div>}
                    <button className="btn-primary"><UsersRound size={18}/> Save family profile</button>
                  </form>
                  {enrollTarget && <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4"><p className="font-bold text-slate-900">Enroll another photo for {people.find(p=>p.id===enrollTarget)?.name}</p><p className="mt-1 text-sm text-slate-600">Add 3–5 varied, sharp photos: front, slight left and right, good daylight, one face only. Re-uploading the same picture won't help.</p><label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" checked={enrollConsent} onChange={e=>setEnrollConsent(e.target.checked)}/> The person gave permission for local face matching.</label><label className={`btn-primary mt-3 inline-flex cursor-pointer ${!enrollConsent || enrollBusy?'opacity-60':''}`}><Upload size={17}/>{enrollBusy?'Enrolling…':'Select face photo'}<input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" disabled={!enrollConsent || enrollBusy} onChange={e=>{enrollPhoto(enrollTarget,e.target.files?.[0]);e.target.value='';}}/></label><button type="button" className="ml-4 text-sm font-bold text-slate-600" onClick={()=>setEnrollTarget(null)}>Cancel</button></div>}
                  <div className="mt-5 space-y-3">
                    {people.map((person) => (
                      <div key={person.id} className="flex items-center gap-3 rounded-2xl bg-slate-50 p-3">
                        <img src={person.photo_url} alt={`${person.name} profile`} className="h-14 w-14 rounded-xl bg-white object-cover" />
                        <div className="min-w-0 flex-1">
                          <div className="font-semibold">{person.name}</div>
                          <div className="text-sm text-slate-600">{person.relationship}</div>
                          <div className="text-sm text-slate-500">{person.description}</div>
                          <div className={`mt-1 text-xs font-semibold ${(recognitionInfo.enrollments?.[person.id] || 0)>0?'text-emerald-700':'text-amber-700'}`}>{recognitionInfo.enrollments?.[person.id] || 0} / 8 face samples · {(recognitionInfo.enrollments?.[person.id] || 0) >= 3 ? 'Ready for testing' : '3+ recommended for reliability'}</div>
                          <div className="mt-2 flex flex-wrap gap-2"><button type="button" className="text-xs font-bold text-emerald-700 hover:underline" onClick={()=>{setEnrollTarget(person.id);setProfileMessage('');}}>+ Add face photo</button>{(recognitionInfo.enrollments?.[person.id] || 0)>0 && <button type="button" className="text-xs font-bold text-rose-600 hover:underline" onClick={()=>deleteEnrollment(person.id)}>Remove samples</button>}</div>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setEditingRecord({ type: 'person', record: person }); setEditMessage(''); }}
                          aria-label={`Edit ${person.name} family profile`}
                          className="rounded-lg p-2 text-sky-700 hover:bg-sky-50"
                        ><Pencil className="h-5 w-5" /></button>
                        <button
                          type="button"
                          onClick={() => handleDelete(`/api/family-members/${person.id}`, `family profile for ${person.name}`)}
                          aria-label={`Delete ${person.name} family profile`}
                          className="rounded-lg p-2 text-rose-700 hover:bg-rose-50"
                        ><Trash2 className="h-5 w-5" /></button>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="panel rounded-3xl p-5">
                  <h3 className="mb-4 text-lg font-semibold">Object records</h3>
                  <form onSubmit={withFormErrors(handleObjectSubmit)} className="grid gap-3">
                    <input name="name" placeholder="Object name" required />
                    <select name="category">
                      <option value="daily">Daily</option>
                      <option value="medical">Medical</option>
                      <option value="travel">Travel</option>
                    </select>
                    <input name="last_location" placeholder="Last known location" required />
                    <textarea name="notes" placeholder="Notes" rows="3" />
                    <button className="rounded-full bg-teal-500 px-4 py-3 font-medium text-white">Save object record</button>
                  </form>
                  <div className="mt-5 space-y-3">
                    {objects.map((object) => (
                      <div key={object.id} className="flex items-start gap-3 rounded-2xl bg-slate-50 p-3">
                        <div className="min-w-0 flex-1">
                          <div className="font-semibold">{object.name}</div>
                          <div className="text-sm text-slate-600">Last seen: {object.last_location}</div>
                          <div className="text-xs text-slate-500">{object.notes || 'No notes available'}</div>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setEditingRecord({ type: 'object', record: object }); setEditMessage(''); }}
                          aria-label={`Edit ${object.name} object record`}
                          className="rounded-lg p-2 text-sky-700 hover:bg-sky-50"
                        ><Pencil className="h-5 w-5" /></button>
                        <button
                          type="button"
                          onClick={() => handleDelete(`/api/objects/${object.id}`, `${object.name} object record`)}
                          aria-label={`Delete ${object.name} object record`}
                          className="rounded-lg p-2 text-rose-700 hover:bg-rose-50"
                        ><Trash2 className="h-5 w-5" /></button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="space-y-6">
                <div className="panel rounded-3xl p-5">
                  <h3 className="mb-4 text-lg font-semibold">Memory library</h3>
                  <form onSubmit={withFormErrors(handleMemorySubmit)} className="grid gap-3">
                    <input name="title" placeholder="Memory title" required />
                    <input name="caption" placeholder="Short caption" />
                    <textarea name="description" placeholder="Story or description" rows="3" />
                    <label className="text-sm font-semibold text-slate-700">Attach photos or videos (optional)
                      <input name="media_files" type="file" multiple accept="image/jpeg,image/png,image/webp,video/mp4,video/webm" className="mt-2" />
                    </label>
                    <p className="text-xs text-slate-500">JPEG, PNG, WebP up to 8 MB each; MP4 or WebM up to 40 MB each. Kept in the local account.</p>
                    <button className="rounded-full bg-sky-600 px-4 py-3 font-medium text-white">Save memory</button>
                  </form>
                  <div className="mt-5 space-y-3">
                    {memories.map((memory) => (
                      <div key={memory.id} className="flex items-start gap-3 rounded-2xl bg-slate-50 p-3">
                        <div className="min-w-0 flex-1">
                          <div className="font-semibold">{memory.title}</div>
                          <div className="text-sm text-slate-600">{memory.caption}</div>
                          <div className="text-xs text-slate-500">{memory.description}</div>
                          <MemoryMediaGallery memory={memory} token={session.token} onDeleteMedia={handleDeleteMemoryMedia}/>
                          <label className="mt-3 block text-xs font-bold text-teal-800">{memoryUploading === memory.id ? 'Uploading…' : 'Add photos / videos'}
                            <input type="file" multiple accept="image/jpeg,image/png,image/webp,video/mp4,video/webm"
                              disabled={memoryUploading === memory.id} className="mt-1 text-xs" onChange={event => { if(event.target.files?.length) handleExistingMemoryFiles(memory.id, event.target.files); event.target.value=''; }} />
                          </label>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setEditingRecord({ type: 'memory', record: memory }); setEditMessage(''); }}
                          aria-label={`Edit memory ${memory.title}`}
                          className="rounded-lg p-2 text-sky-700 hover:bg-sky-50"
                        ><Pencil className="h-5 w-5" /></button>
                        <button
                          type="button"
                          onClick={() => handleDelete(`/api/memories/${memory.id}`, `memory ${memory.title}`)}
                          aria-label={`Delete memory ${memory.title}`}
                          className="rounded-lg p-2 text-rose-700 hover:bg-rose-50"
                        ><Trash2 className="h-5 w-5" /></button>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="panel rounded-3xl p-5">
                  <h3 className="mb-4 text-lg font-semibold">Reminder & schedule</h3>
                  <form onSubmit={withFormErrors(handleScheduleSubmit)} className="mb-4 grid gap-3">
                    <input name="title" placeholder="Schedule title" required />
                    <input name="scheduled_for" type="datetime-local" required />
                    <textarea name="notes" rows="2" placeholder="Notes" />
                    <button className="rounded-full bg-indigo-600 px-4 py-3 font-medium text-white">Add schedule</button>
                  </form>
                  <form onSubmit={withFormErrors(handleReminderSubmit)} className="grid gap-3">
                    <input name="title" placeholder="Reminder title" required />
                    <input name="reminder_time" type="datetime-local" required />
                    <textarea name="notes" rows="2" placeholder="Reminder details" />
                    <button className="rounded-full bg-amber-500 px-4 py-3 font-medium text-white">Add reminder</button>
                  </form>
                  <div className="mt-5 space-y-3">
                    {orderedAgenda.map(item => (
                      <div key={`${item.kind}-${item.id}`} className="flex items-start gap-3 rounded-2xl bg-slate-50 p-3">
                        <div className="min-w-0 flex-1">
                          <div className="text-xs font-bold uppercase tracking-wider text-teal-700">{item.kind}</div>
                          <div className="font-semibold">{item.title}</div>
                          <div className="text-sm text-slate-600">{new Date(item.time).toLocaleString()}</div>
                          <div className="text-xs text-slate-500">{item.notes}</div>
                        </div>
                        <button type="button" onClick={() => { setEditingRecord({ type: item.kind, record: item }); setEditMessage(''); }}
                          aria-label={`Edit ${item.kind} ${item.title}`} className="rounded-lg p-2 text-sky-700 hover:bg-sky-50"><Pencil className="h-5 w-5" /></button>
                        <button type="button" onClick={() => handleDelete(`/api/${item.kind === 'schedule' ? 'schedule' : 'reminders'}/${item.id}`, `${item.kind} ${item.title}`)}
                          aria-label={`Delete ${item.kind} ${item.title}`} className="rounded-lg p-2 text-rose-700 hover:bg-rose-50"><Trash2 className="h-5 w-5" /></button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <div className="panel rounded-3xl p-5">
                <h3 className="mb-4 text-lg font-semibold">Preferences</h3>
                <form onSubmit={withFormErrors(handlePreferenceSubmit)} className="grid gap-3">
                  <select name="response_mode">
                    <option value="text">Text</option>
                    <option value="voice">Voice</option>
                    <option value="hybrid">Hybrid</option>
                  </select>
                  <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="voice_first" /> Voice-first responses</label>
                  <select name="detail_level">
                    <option value="brief">Brief</option>
                    <option value="medium">Medium</option>
                    <option value="detailed">Detailed</option>
                  </select>
                  <select name="reminder_format">
                    <option value="text">Text reminder</option>
                    <option value="voice">Voice reminder</option>
                    <option value="visual">Visual reminder</option>
                  </select>
                  <button className="rounded-full bg-sky-600 px-4 py-3 font-medium text-white">Update preferences</button>
                </form>
              </div>

              <div className="panel rounded-3xl p-5">
                <h3 className="mb-4 text-lg font-semibold">Emergency contacts</h3>
                <form onSubmit={withFormErrors(handleEmergencySubmit)} className="grid gap-3">
                  <input name="name" placeholder="Emergency contact name" required />
                  <input name="phone" placeholder="Phone number" required />
                  <input name="relationship" placeholder="Relationship" defaultValue="caregiver" />
                  <button className="rounded-full bg-rose-500 px-4 py-3 font-medium text-white">Add contact</button>
                </form>
                <div className="mt-5 space-y-3">
                  {emergencyContacts.map((contact) => (
                    <div key={contact.id} className="flex items-center gap-3 rounded-2xl bg-slate-50 p-3">
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold">{contact.name}</div>
                        <div className="text-sm text-slate-600">{contact.relationship} · {contact.phone}</div>
                      </div>
                      <button
                        type="button"
                        onClick={() => { setEditingRecord({ type: 'emergency', record: contact }); setEditMessage(''); }}
                        aria-label={`Edit emergency contact ${contact.name}`}
                        className="rounded-lg p-2 text-sky-700 hover:bg-sky-50"
                      ><Pencil className="h-5 w-5" /></button>
                      <button
                        type="button"
                        onClick={() => handleDelete(`/api/emergency/${contact.id}`, `emergency contact ${contact.name}`)}
                        aria-label={`Delete emergency contact ${contact.name}`}
                        className="rounded-lg p-2 text-rose-700 hover:bg-rose-50"
                      ><Trash2 className="h-5 w-5" /></button>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="panel rounded-3xl p-5">
              <h3 className="mb-4 text-lg font-semibold">Audit history</h3>
              <div className="space-y-3">
                {auditLog.length ? auditLog.map((log) => (
                  <div key={log.id} className="rounded-2xl bg-slate-50 p-3 text-sm">
                    <div className="font-medium">{log.action}</div>
                    <div className="text-slate-600">{log.details}</div>
                  </div>
                )) : <div className="text-slate-500">No audit entries yet.</div>}
              </div>
            </div>

            {editingRecord && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4" role="presentation">
                <form
                  key={`${editingRecord.type}-${editingRecord.record.id}`}
                  onSubmit={handleEditSubmit}
                  role="dialog"
                  aria-modal="true"
                  aria-labelledby="edit-record-title"
                  className="panel w-full max-w-lg space-y-4 rounded-3xl p-6"
                >
                  <h3 id="edit-record-title" className="text-xl font-bold">Edit saved record</h3>
                  {editingRecord.type === 'person' && (
                    <>
                      <input name="name" aria-label="Name" defaultValue={editingRecord.record.name} required />
                      <input name="relationship" aria-label="Relationship" defaultValue={editingRecord.record.relationship} required />
                      <textarea name="description" aria-label="Description" defaultValue={editingRecord.record.description} rows="3" />
                    </>
                  )}
                  {editingRecord.type === 'object' && (
                    <>
                      <input name="name" aria-label="Object name" defaultValue={editingRecord.record.name} required />
                      <select name="category" aria-label="Category" defaultValue={editingRecord.record.category}>
                        <option value="daily">Daily</option>
                        <option value="medical">Medical</option>
                        <option value="travel">Travel</option>
                        <option value="personal">Personal</option>
                      </select>
                      <input name="last_location" aria-label="Last known location" defaultValue={editingRecord.record.last_location} required />
                      <textarea name="notes" aria-label="Notes" defaultValue={editingRecord.record.notes} rows="3" />
                    </>
                  )}
                  {editingRecord.type === 'memory' && (
                    <>
                      <input name="title" aria-label="Title" defaultValue={editingRecord.record.title} required />
                      <input name="caption" aria-label="Caption" defaultValue={editingRecord.record.caption} />
                      <textarea name="description" aria-label="Description" defaultValue={editingRecord.record.description} rows="3" />
                    </>
                  )}
                  {editingRecord.type === 'schedule' && (
                    <>
                      <input name="title" aria-label="Title" defaultValue={editingRecord.record.title} required />
                      <input name="scheduled_for" type="datetime-local" aria-label="Scheduled time" defaultValue={datetimeLocalValue(editingRecord.record.scheduled_for)} required />
                      <textarea name="notes" aria-label="Notes" defaultValue={editingRecord.record.notes} rows="3" />
                    </>
                  )}
                  {editingRecord.type === 'reminder' && (
                    <>
                      <input name="title" aria-label="Title" defaultValue={editingRecord.record.title} required />
                      <input name="reminder_time" type="datetime-local" aria-label="Reminder time" defaultValue={datetimeLocalValue(editingRecord.record.reminder_time)} required />
                      <textarea name="notes" aria-label="Notes" defaultValue={editingRecord.record.notes} rows="3" />
                    </>
                  )}
                  {editingRecord.type === 'emergency' && (
                    <>
                      <input name="name" aria-label="Name" defaultValue={editingRecord.record.name} required />
                      <input name="phone" aria-label="Phone number" defaultValue={editingRecord.record.phone} required />
                      <input name="relationship" aria-label="Relationship" defaultValue={editingRecord.record.relationship} required />
                    </>
                  )}
                  {editMessage && <div className="text-sm text-rose-700" role="alert">{editMessage}</div>}
                  <div className="flex justify-end gap-3">
                    <button type="button" onClick={() => setEditingRecord(null)} className="rounded-full border border-slate-200 bg-white px-4 py-2">Cancel</button>
                    <button type="submit" className="rounded-full bg-sky-600 px-4 py-2 font-medium text-white">Save changes</button>
                  </div>
                </form>
              </div>
            )}
          </section>
        )}

        {activeView === 'object' && (
          <section className="panel rounded-3xl p-6">
            <div className="mb-4 flex items-center gap-3"><Search className="h-6 w-6 text-sky-600" /> <h2 className="text-2xl font-bold">Object Memory Finder</h2></div>
            <p className="mb-4 text-sm text-slate-600">Ask about something, like a pen or glasses. ReMind checks caregiver-saved locations and records the request for the caregiver dashboard. No camera tracking is involved.</p>
            <form onSubmit={event=>{event.preventDefault();lookupObject(objectLookupName);}} className="mb-4 flex flex-col gap-2 sm:flex-row">
              <input aria-label="Object to find" value={objectLookupName} onChange={event=>setObjectLookupName(event.target.value)} maxLength={80} placeholder="Enter an item, e.g. pen" required className="flex-1" />
              <button type="submit" className="rounded-xl bg-sky-600 px-4 py-3 font-bold text-white disabled:opacity-50" disabled={objectLookupBusy}>{objectLookupBusy?'Searching…':'Find this item'}</button>
            </form>
            <div className="mb-4 flex flex-wrap items-center gap-2">{['Pen','Glasses','Keys','Phone','Wallet','Cup'].map(name=><button key={name} type="button" onClick={()=>lookupObject(name)} className="rounded-full border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-800">{name}</button>)}</div>
            {objectLookupResult && <div role="status" className={`mb-5 rounded-xl border p-4 ${objectLookupResult.found?'border-emerald-200 bg-emerald-50 text-emerald-900':'border-amber-200 bg-amber-50 text-amber-900'}`}>
              <p className="font-bold">{objectLookupResult.answer}</p>
              <p className="mt-1 text-xs">Request recorded in caregiver activity. A saved location is not live item tracking.</p>
            </div>}
            <div className="grid gap-4 md:grid-cols-2">
              {objects.map((item) => (
                <div key={item.id} className="rounded-2xl bg-slate-50 p-4">
                  <div className="font-semibold">{item.name}</div>
                  <div className="text-sm text-slate-600">Last recorded: {item.last_location}</div>
                  <div className="mt-2 text-sm text-slate-500">{item.notes}</div>
                  <button type="button" disabled={objectLookupBusy} onClick={()=>lookupObject(item.name)} className="mt-3 inline-flex items-center gap-2 rounded-xl bg-white px-3 py-2 text-sm font-bold text-sky-700 shadow-sm"><Search size={16}/> Ask about {item.name}</button>
                </div>
              ))}
            </div>
          </section>
        )}

        {activeView === 'memory' && (
          <section className="panel rounded-3xl p-6">
            <div className="mb-4 flex items-center gap-3"><ImageIcon className="h-6 w-6 text-sky-600" /> <h2 className="text-2xl font-bold">Personal Memory Library</h2></div>
            <div className="grid gap-4 md:grid-cols-2">
              {memories.map((memory) => (
                <div key={memory.id} className="rounded-2xl bg-slate-50 p-4">
                  <div className="font-semibold">{memory.title}</div>
                  <div className="text-sm text-slate-600">{memory.caption}</div>
                  <div className="mt-2 text-sm text-slate-500">{memory.description}</div>
                  <MemoryMediaGallery memory={memory} token={session.token}/>
                </div>
              ))}
            </div>
          </section>
        )}

        {activeView === 'schedule' && (
          <section className="panel rounded-3xl p-6">
            <div className="mb-4 flex items-center gap-3"><CalendarDays className="h-6 w-6 text-sky-600" /> <h2 className="text-2xl font-bold">My Daily Schedule</h2></div>
            <div className="space-y-3">
              {orderedAgenda.map(item => (
                <div key={`${item.kind}-${item.id}`} className="rounded-2xl bg-slate-50 p-4">
                  <div className="text-xs font-bold uppercase text-teal-700">{item.kind}</div>
                  <div className="font-semibold">{item.title}</div>
                  <div className="text-sm text-slate-600">{new Date(item.time).toLocaleString()}</div>
                  <div className="text-sm text-slate-500">{item.notes}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {activeView === 'voice' && (
          <section className="panel rounded-3xl p-6">
            <div className="mb-4 flex items-center gap-3"><Mic className="h-6 w-6 text-sky-600" /> <h2 className="text-2xl font-bold">Voice Companion</h2></div>
            <div className="flex flex-wrap gap-4">
              <button onClick={startListening} className="rounded-full bg-sky-600 px-5 py-3 font-medium text-white">{isListening ? 'Listening...' : 'Speak now'}</button>
              <button onClick={() => speak(assistantAnswer)} className="rounded-full border border-slate-200 bg-white px-5 py-3 font-medium text-slate-700">Read answer aloud</button>
            </div>
            <div className="mt-4 rounded-2xl bg-sky-50 p-4 text-sm">{assistantAnswer}</div>
          </section>
        )}

        {activeView === 'help' && (
          <section className="panel rounded-3xl p-6">
            <div className="mb-4 flex items-center gap-3"><ShieldAlert className="h-6 w-6 text-rose-600" /> <h2 className="text-2xl font-bold">Safety Assistance</h2></div>
            <p className="mb-4 text-sm text-slate-600">Choose an approved contact below to start a call. No automatic calls are made.</p>
            <div className="space-y-3">
              {emergencyContacts.length === 0 && <p>No emergency contacts saved. Ask a trusted caregiver to add one in the dashboard.</p>}
              {emergencyContacts.map((contact) => (
                <div key={contact.id} className="rounded-2xl bg-slate-50 p-4">
                  <div className="font-semibold">{contact.name}</div>
                  <div className="text-sm text-slate-600">{contact.relationship}</div>
                  <a className="mt-2 inline-flex items-center gap-2 rounded-full bg-sky-600 px-4 py-2 text-sm font-medium text-white" href={`tel:${contact.phone.replace(/[^+0-9]/g, '')}`}><Phone className="h-4 w-4" /> Call {contact.name}</a>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
