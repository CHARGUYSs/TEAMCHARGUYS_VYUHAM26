import { useCallback, useEffect, useState } from 'react';
import { Activity, Check, ClipboardList, Clock3, RotateCw, ShieldCheck, Trash2 } from 'lucide-react';

async function request(path, token, options = {}) {
  const response = await fetch(path, {
    cache: 'no-store',
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }
  return payload;
}

const localDate = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
};

function ErrorMessage({ children }) {
  return children ? <p role="alert" className="mt-3 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{children}</p> : null;
}

export function PatientDaily({ token }) {
  const [tasks, setTasks] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);
  const [feedback, setFeedback] = useState({});
  const [quizMessage, setQuizMessage] = useState('');
  const [refreshingQuiz, setRefreshingQuiz] = useState(false);

  const load = useCallback(async () => {
    setError('');
    try {
      const [dailyTasks, quiz] = await Promise.all([
        request('/api/daily-tasks?upcoming_days=14', token),
        request('/api/daily-quiz', token),
      ]);
      setTasks(dailyTasks);
      setQuestions(quiz.questions || []);
    } catch (loadError) {
      setError(loadError.message || 'Could not load today’s activities.');
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const refreshQuestions = async () => {
    setRefreshingQuiz(true);
    setError('');
    try {
      const result = await request('/api/daily-quiz/refresh', token, { method: 'POST' });
      setQuestions(result.questions || []);
      setQuizMessage(result.message || 'Questions refreshed.');
      setFeedback({});
      // Other patient tasks may have been updated by the caregiver meanwhile.
      setTasks(await request('/api/daily-tasks?upcoming_days=14', token));
    } catch (refreshError) {
      setError(refreshError.message || 'Could not refresh the friendly questions.');
    } finally { setRefreshingQuiz(false); }
  };

  const completeTask = async (taskId) => {
    setBusyId(taskId);
    setError('');
    try {
      const updated = await request(`/api/daily-tasks/${taskId}/complete`, token, { method: 'POST' });
      setTasks((current) => current.map((task) => task.id === taskId ? updated : task));
    } catch (actionError) {
      setError(actionError.message || 'Could not update this task.');
    } finally {
      setBusyId(null);
    }
  };

  const answerQuestion = async (question, answer) => {
    setBusyId(question.id);
    setError('');
    try {
      const result = await request(`/api/daily-quiz/${question.id}/answer`, token, {
        method: 'POST',
        body: JSON.stringify({ answer }),
      });
      setQuestions((current) => current.map((item) => item.id === question.id ? result.question : item));
      setFeedback((current) => ({
        ...current,
        [question.id]: result.question.is_correct
          ? 'That’s right!'
          : `Good try. The answer is ${result.correct_answer}.`,
      }));
    } catch (actionError) {
      setError(actionError.message || 'Could not save your answer.');
      await load();
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="panel mb-7 rounded-3xl p-5 md:p-7" aria-labelledby="daily-check-in-title">
      <div className="flex items-start gap-3">
        <div className="rounded-2xl bg-emerald-100 p-3 text-emerald-800"><ClipboardList size={22} /></div>
        <div>
          <p className="eyebrow">A GENTLE DAILY CHECK-IN</p>
          <h2 id="daily-check-in-title" className="section-heading">Today’s activities</h2>
          <p className="mt-1 text-sm text-slate-600">A helpful routine and a few friendly memory questions.</p>
        </div>
        <button type="button" onClick={load} className="btn-outline ml-auto !px-3 !py-2" aria-label="Refresh daily activities">
          <RotateCw size={17} />
        </button>
      </div>
      <ErrorMessage>{error}</ErrorMessage>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl bg-slate-50 p-4">
          <h3 className="font-extrabold text-slate-800">My daily tasks · earliest first</h3>
          {tasks.length ? <ul className="mt-3 space-y-2">
            {tasks.map((task) => {
              const done = task.completed_by_patient || task.verification_status === 'verified';
              return <li key={task.id} className="flex items-start gap-3 rounded-xl bg-white p-3">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-bold text-emerald-700">{task.task_date === localDate() ? 'Today' : new Date(`${task.task_date}T12:00:00`).toLocaleDateString(undefined, { dateStyle: 'medium' })}</p>
                  <p className="font-bold text-slate-800">{task.title}</p>
                  {task.notes && <p className="mt-1 text-sm text-slate-600">{task.notes}</p>}
                  {task.completed_by_patient && task.verification_status === 'pending' &&
                    <p className="mt-1 text-xs font-semibold text-amber-700">Done — waiting for caregiver review</p>}
                  {task.verification_status === 'rejected' &&
                    <p className="mt-1 text-xs font-semibold text-rose-700">Please check with your caregiver{task.caregiver_comment ? `: ${task.caregiver_comment}` : '.'}</p>}
                </div>
                <button type="button" disabled={done || busyId === task.id || task.task_date !== localDate()} onClick={() => completeTask(task.id)}
                  className={done ? 'rounded-xl bg-emerald-100 px-3 py-2 text-sm font-bold text-emerald-800' : 'btn-soft !px-3 !py-2'}>
                  {done ? <><Check size={16} /> Done</> : task.task_date !== localDate() ? 'Upcoming' : 'Mark done'}
                </button>
              </li>;
            })}
          </ul> : <p className="mt-3 text-sm text-slate-500">No tasks have been added for today.</p>}
        </div>

        <div className="rounded-2xl bg-slate-50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-extrabold text-slate-800">A few friendly questions</h3>
            <button type="button" className="btn-outline !px-3 !py-2 text-xs" disabled={refreshingQuiz}
              onClick={refreshQuestions}><RotateCw size={15} /> {refreshingQuiz ? 'Refreshing…' : 'New questions'}</button>
          </div>
          {quizMessage && <p role="status" className="mt-2 text-xs text-teal-800">{quizMessage}</p>}
          {questions.length ? <ol className="mt-3 space-y-3">
            {questions.map((question) => <li key={question.id} className="rounded-xl bg-white p-3">
              <p className="font-bold text-slate-800">{question.question_text}</p>
              {question.answered ? <p className="mt-2 text-sm font-semibold text-emerald-700">
                {feedback[question.id] || 'You answered this question today.'}
              </p> : <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {question.options.map((option) => <button key={option} type="button"
                  disabled={busyId === question.id} onClick={() => answerQuestion(question, option)}
                  className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-sm font-semibold text-slate-700 hover:border-emerald-300 hover:bg-emerald-50">
                  {option}
                </button>)}
              </div>}
            </li>)}
          </ol> : <p className="mt-3 text-sm text-slate-500">No questions are available right now.</p>}
        </div>
      </div>
      <p className="mt-4 text-xs leading-relaxed text-slate-500">
        <ShieldCheck size={14} className="mr-1 inline" />
        These are optional activities, not a medical test or diagnosis.
      </p>
    </section>
  );
}

export function CaregiverWorkspace({ token, onNotificationChange, onRecordChanged }) {
  const [requests, setRequests] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [achievement, setAchievement] = useState(null);
  const [quizTrends, setQuizTrends] = useState(null);
  const [title, setTitle] = useState('');
  const [notes, setNotes] = useState('');
  const [taskDate, setTaskDate] = useState(localDate());
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError('');
    try {
      const [inbox, todayTasks, taskSummary, quizSummary] = await Promise.all([
        request('/api/caregiver/notifications', token),
        request('/api/caregiver/daily-tasks', token),
        request('/api/caregiver/task-achievement?days=30', token),
        request('/api/caregiver/quiz-trends?days=30', token),
      ]);
      setRequests(inbox.items || []);
      setTasks(todayTasks);
      setAchievement(taskSummary);
      setQuizTrends(quizSummary);
      onNotificationChange?.(inbox.count || 0);
    } catch (loadError) {
      setError(loadError.message || 'Could not load caregiver information.');
    }
  }, [token, onNotificationChange]);

  useEffect(() => {
    load();
    const timer = window.setInterval(async () => {
      try {
        const inbox = await request('/api/caregiver/notifications', token);
        setRequests(inbox.items || []);
        onNotificationChange?.(inbox.count || 0);
      } catch (loadError) {
        setError(loadError.message || 'Could not refresh caregiver requests.');
      }
    }, 20000);
    return () => window.clearInterval(timer);
  }, [load, token, onNotificationChange]);

  const perform = async (operation) => {
    setBusy(true);
    setError('');
    try {
      await operation();
      await load();
      await onRecordChanged?.();
    } catch (actionError) {
      setError(actionError.message || 'Could not save this change.');
    } finally {
      setBusy(false);
    }
  };

  const addTask = (event) => {
    event.preventDefault();
    const taskTitle = title.trim();
    if (!taskTitle) return;
    perform(async () => {
      await request('/api/caregiver/daily-tasks', token, {
        method: 'POST',
        body: JSON.stringify({ title: taskTitle, notes: notes.trim(), task_date: taskDate }),
      });
      setTitle('');
      setNotes('');
      setTaskDate(localDate());
    });
  };

  return (
    <section className="panel rounded-3xl p-5 md:p-7" aria-labelledby="caregiver-workspace-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="eyebrow">CAREGIVER WORKSPACE</p>
          <h3 id="caregiver-workspace-title" className="section-heading">Requests & daily support</h3>
          <p className="mt-1 text-sm text-slate-600">Review requests and schedule tasks by date; the earliest date appears first.</p>
        </div>
        <button type="button" onClick={load} className="btn-outline !px-3 !py-2" aria-label="Refresh caregiver workspace">
          <RotateCw size={17} /> Refresh
        </button>
      </div>
      <ErrorMessage>{error}</ErrorMessage>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl bg-amber-50/70 p-4">
          <h4 className="font-extrabold text-slate-800">Patient requests</h4>
          {requests.length ? <ul className="mt-3 space-y-2">
            {requests.map((item) => <li key={`${item.kind}-${item.id}`} className="flex items-center gap-3 rounded-xl bg-white p-3">
              <div className="min-w-0 flex-1">
                <p className="font-bold capitalize text-slate-800">{item.name} <span className="font-normal text-slate-500">· {item.kind}</span></p>
                <p className="mt-1 text-xs text-slate-500">{item.count} request{item.count === 1 ? '' : 's'} · {new Date(item.at).toLocaleString()}</p>
              </div>
              <button type="button" disabled={busy} onClick={() => perform(() => request(
                `/api/caregiver/requests/${item.kind}/${item.id}/dismiss`, token, { method: 'POST' },
              ))} className="btn-outline !px-3 !py-2 text-xs">Dismiss</button>
            </li>)}
          </ul> : <p className="mt-3 text-sm text-slate-500">No open requests.</p>}
        </div>

        <div className="rounded-2xl bg-slate-50 p-4">
          <h4 className="font-extrabold text-slate-800">Assign a dated task</h4>
          <form onSubmit={addTask} className="mt-3 space-y-2">
            <label className="sr-only" htmlFor="care-task-title">Task title</label>
            <input id="care-task-title" value={title} onChange={(event) => setTitle(event.target.value)}
              maxLength={160} placeholder="e.g. Take the morning walk" required />
            <label className="sr-only" htmlFor="care-task-notes">Task notes</label>
            <input id="care-task-notes" value={notes} onChange={(event) => setNotes(event.target.value)}
              maxLength={1000} placeholder="Optional reminder" />
            <label className="block text-xs font-bold text-slate-600" htmlFor="care-task-date">Task date</label>
            <input id="care-task-date" type="date" value={taskDate} onChange={(event) => setTaskDate(event.target.value)} required />
            <button type="submit" disabled={busy || !title.trim() || !taskDate} className="btn-primary !py-2.5">Assign task</button>
          </form>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-slate-100 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h4 className="inline-flex items-center gap-2 font-extrabold text-slate-800"><ClipboardList size={18} /> Assigned tasks · date ascending</h4>
          <span className="text-sm text-slate-600">{achievement?.completion_rate ?? 0}% reported complete in the last 30 days</span>
        </div>
        {tasks.length ? <ul className="mt-3 divide-y divide-slate-100">
          {tasks.map((task) => <li key={task.id} className="flex flex-wrap items-center gap-3 py-3">
            <div className="min-w-0 flex-1">
              <p className="text-xs font-bold text-teal-800">{new Date(`${task.task_date}T12:00:00`).toLocaleDateString(undefined, { dateStyle: 'medium' })}</p>
              <p className="font-bold text-slate-800">{task.title}</p>
              <p className="mt-1 text-xs text-slate-500">
                {task.completed_by_patient ? 'Patient reported complete' : 'Not completed yet'}
                {' · '}Review: {task.verification_status}
                {task.caregiver_comment ? ` · ${task.caregiver_comment}` : ''}
              </p>
            </div>
            <button type="button" disabled={busy || task.task_date > localDate()} onClick={() => perform(() => request(
              `/api/caregiver/daily-tasks/${task.id}/verify`, token,
              { method: 'POST', body: JSON.stringify({ status: 'verified', comment: '' }) },
            ))} className="btn-soft !px-3 !py-2 text-xs"><Check size={15} /> Verify</button>
            {task.completed_by_patient && task.verification_status === 'pending' &&
              <button type="button" disabled={busy} onClick={() => perform(() => request(
                `/api/caregiver/daily-tasks/${task.id}/verify`, token,
                { method: 'POST', body: JSON.stringify({ status: 'rejected', comment: '' }) },
              ))} className="btn-outline !px-3 !py-2 text-xs">Review</button>}
            <button type="button" disabled={busy} onClick={() => perform(() => request(
              `/api/caregiver/daily-tasks/${task.id}`, token, { method: 'DELETE' },
            ))} className="rounded-xl p-2 text-rose-700 hover:bg-rose-50" aria-label={`Delete ${task.title}`}>
              <Trash2 size={17} />
            </button>
          </li>)}
        </ul> : <p className="mt-3 text-sm text-slate-500">No tasks assigned yet.</p>}
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <div className="rounded-2xl bg-emerald-50 p-4">
          <p className="text-sm font-bold text-emerald-900"><Activity size={16} className="mr-1 inline" /> Recall check-in · last 30 days</p>
          <p className="mt-2 text-2xl font-extrabold text-emerald-900">
            {quizTrends?.correct_answers ?? 0} / {quizTrends?.answered_questions ?? 0} correct
          </p>
          <p className="mt-1 text-xs text-emerald-800">{quizTrends?.disclaimer || 'Usage trend only; not a medical assessment.'}</p>
          <div className="mt-3 rounded-xl border border-emerald-200 bg-white/80 p-3">
            <p className="text-sm font-extrabold text-slate-800">Tracking Phase {quizTrends?.tracking_phase_number ?? 1}: {quizTrends?.tracking_phase ?? 'Starting baseline'}</p>
            <p className="mt-1 text-xs text-slate-600">{quizTrends?.answered_questions ?? 0} assessments answered across {quizTrends?.assessment_days ?? 0} days · {quizTrends?.questions_asked ?? 0} patient questions asked</p>
            <p className="mt-1 text-xs text-slate-500">Data coverage only. This is NOT a dementia, Alzheimer's, or cognitive disease stage.</p>
          </div>
        </div>
        <div className="rounded-2xl bg-sky-50 p-4">
          <p className="text-sm font-bold text-sky-900"><Clock3 size={16} className="mr-1 inline" /> Caregiver review</p>
          <p className="mt-2 text-2xl font-extrabold text-sky-900">{achievement?.pending_review ?? 0} awaiting review</p>
          <p className="mt-1 text-xs text-sky-800">Patient-reported completion is not independently verified.</p>
        </div>
      </div>
    </section>
  );
}
