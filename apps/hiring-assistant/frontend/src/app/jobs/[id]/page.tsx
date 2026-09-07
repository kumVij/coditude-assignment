"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, type Candidate, type Job, type ScreeningCall } from "@/lib/api";
import { ChevronDown, ExternalLink, Headphones, Plus, Radio, Sparkles } from "lucide-react";
import { useParams } from "next/navigation";
import { Fragment, useCallback, useEffect, useState } from "react";

const STATUS_VARIANT: Record<string, "default" | "success" | "warning" | "destructive" | "outline"> = {
  COMPLETED: "success",
  IN_PROGRESS: "warning",
  RINGING: "warning",
  SCHEDULED: "outline",
  NOT_STARTED: "outline",
  NOT_CONNECTED: "destructive",
  FAILED: "destructive",
  CANCELLED: "destructive",
};

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const jobId = params.id;

  const [job, setJob] = useState<Job | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [calls, setCalls] = useState<ScreeningCall[]>([]);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [expandedCallId, setExpandedCallId] = useState<string | null>(null);

  const completedCalls = calls.filter((call) => call.status === "COMPLETED").length;
  const activeCalls = calls.filter((call) => ["SCHEDULED", "RINGING", "IN_PROGRESS"].includes(call.status)).length;
  const connectedCalls = calls.filter((call) => call.result?.reachable === true).length;

  const loadAll = useCallback(async () => {
    try {
      const [j, c, calls] = await Promise.all([
        api.getJob(jobId),
        api.listCandidates(jobId),
        api.listCalls(jobId),
      ]);
      setJob(j);
      setCandidates(c);
      setCalls(calls);
    } catch (e) {
      setError(String(e));
    }
  }, [jobId]);

  useEffect(() => {
    loadAll();
    // Poll every 8s as a fallback to webhooks (useful for local dev without a public URL)
    const interval = setInterval(async () => {
      try {
        setCalls(await api.listCalls(jobId, true));
      } catch {
        /* ignore transient polling errors */
      }
    }, 8000);
    return () => clearInterval(interval);
  }, [jobId, loadAll]);

  const handleProvision = async () => {
    setBusy("provision");
    setError(null);
    setNotice(null);
    try {
      const updated = await api.provisionAgent(jobId);
      setJob(updated);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const handleAddCandidate = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy("add-candidate");
    setError(null);
    setNotice(null);
    try {
      await api.addCandidates(jobId, [{ name, mobile_number: phone, consent_obtained: consent }]);
      setName("");
      setPhone("");
      setConsent(false);
      setCandidates(await api.listCandidates(jobId));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const handleScreenAll = async () => {
    setBusy("screen");
    setError(null);
    setNotice(null);
    try {
      const batch = await api.startScreening(jobId);
      setCalls(await api.listCalls(jobId));
      setNotice(`${batch.candidate_count} call request${batch.candidate_count === 1 ? "" : "s"} queued. Batch ${batch.batch_id.slice(0, 8)} is being processed.`);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const handleScreenCandidate = async (candidateId: string) => {
    setBusy(`screen-${candidateId}`);
    setError(null);
    setNotice(null);
    try {
      const batch = await api.startScreening(jobId, [candidateId]);
      setCalls(await api.listCalls(jobId));
      setNotice(`Call queued. Batch ${batch.batch_id.slice(0, 8)} is being processed; watch Screening calls for status updates.`);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const handleConsent = async (candidateId: string) => {
    setBusy(`consent-${candidateId}`);
    setError(null);
    try {
      await api.recordConsent(jobId, candidateId);
      setCandidates(await api.listCandidates(jobId));
      setNotice("Consent recorded. You can now call this candidate.");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  if (!job) {
    return <p className="text-sm text-muted-foreground">Loading job...</p>;
  }

  return (
    <main className="flex flex-col gap-7">
      <header className="hero-panel">
        <div className="relative z-10 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="max-w-3xl">
            <div className="eyebrow"><Sparkles size={14} /> Hiring workspace</div>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-4xl">{job.title}</h1>
            <p className="mt-3 line-clamp-3 max-w-2xl text-sm leading-6 text-slate-300">{job.description}</p>
          </div>
          <Badge variant={job.hunar_agent_id ? "success" : "outline"} className="w-fit border-white/10 bg-white/10 text-white">
            <span className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full ${job.hunar_agent_id ? "bg-emerald-300" : "bg-amber-300"}`} />
            {job.hunar_agent_id ? "Agent ready" : "Agent not provisioned"}
          </Badge>
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-3" aria-label="Screening overview">
        <div className="metric-card"><span>Total calls</span><strong>{calls.length}</strong><small>Across this role</small></div>
        <div className="metric-card"><span>Completed</span><strong>{completedCalls}</strong><small>{connectedCalls} connected</small></div>
        <div className="metric-card"><span>In progress</span><strong>{activeCalls}</strong><small>Updates every 8 seconds</small></div>
      </section>

      {error && (
        <p className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </p>
      )}

      {notice && (
        <p role="status" className="flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
          {notice}
        </p>
      )}

      {!job.hunar_agent_id && (
        <Card className="border-amber-200 bg-amber-50/70">
          <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-amber-950">
              Provision the Hunar voice agent for this role before you can start screening calls.
            </p>
            <Button className="shrink-0" onClick={handleProvision} disabled={busy === "provision"}>
              {busy === "provision" ? "Provisioning..." : "Provision agent"}
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="section-heading">
          <div><p className="section-kicker">Talent pool</p><CardTitle>Add candidate</CardTitle></div>
          <span className="section-count">{candidates.length} {candidates.length === 1 ? "candidate" : "candidates"}</span>
        </CardHeader>
        <CardContent>
          <form className="flex flex-wrap items-end gap-3" onSubmit={handleAddCandidate}>
            <div className="grid min-w-48 flex-1 gap-1.5">
              <Label htmlFor="cname">Name</Label>
              <Input id="cname" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="grid min-w-64 flex-[1.4] gap-1.5">
              <Label htmlFor="cphone">Mobile (E.164, e.g. +919876543210)</Label>
              <Input id="cphone" value={phone} onChange={(e) => setPhone(e.target.value)} required />
            </div>
            <label className="flex h-9 items-center gap-2 text-xs text-muted-foreground">
              <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
              Candidate consent received
            </label>
            <Button type="submit" size="icon" aria-label="Add candidate" title="Add candidate" disabled={busy === "add-candidate"}>
              <Plus size={17} />
            </Button>
          </form>

          <Table className="mt-4">
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Mobile</TableHead>
                <TableHead><span className="sr-only">Action</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {candidates.map((c) => (
                <TableRow key={c.id}>
                  <TableCell>{c.name}</TableCell>
                  <TableCell>{c.mobile_number}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      {!c.consent_obtained && (
                        <Button variant="outline" size="sm" onClick={() => handleConsent(c.id)} disabled={busy !== null}>
                          {busy === `consent-${c.id}` ? "Saving..." : "Record consent"}
                        </Button>
                      )}
                      <Button variant="outline" size="sm" onClick={() => handleScreenCandidate(c.id)} disabled={!job.hunar_agent_id || !c.consent_obtained || busy !== null}>
                        <Radio size={14} />
                        {busy === `screen-${c.id}` ? "Calling..." : "Call"}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {candidates.length === 0 && (
                <TableRow>
                  <TableCell colSpan={3} className="text-muted-foreground">
                    No candidates yet.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="section-heading gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div><p className="section-kicker">Live activity</p><CardTitle>Screening calls</CardTitle></div>
          <Button
            className="w-full sm:w-auto"
            onClick={handleScreenAll}
            disabled={!job.hunar_agent_id || candidates.length === 0 || busy === "screen"}
          >
            <Radio size={16} />
            {busy === "screen" ? "Starting all calls..." : "Call all candidates"}
          </Button>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Candidate</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Recommendation</TableHead>
                <TableHead>Recording</TableHead>
                <TableHead><span className="sr-only">Details</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {calls.map((call) => (
                <Fragment key={call.id}>
                <TableRow>
                  <TableCell className="font-medium">{call.candidate.name}</TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANT[call.status] ?? "outline"}>{call.status}</Badge>
                  </TableCell>
                  <TableCell>{call.duration_minutes ? `${call.duration_minutes.toFixed(1)} min` : "—"}</TableCell>
                  <TableCell>
                    {typeof call.result?.recommendation === "string" ? call.result.recommendation : "—"}
                  </TableCell>
                  <TableCell>
                    {call.recording_url ? (
                      <a
                        className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                        href={call.recording_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <Headphones size={14} /> Listen
                      </a>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={expandedCallId === call.id ? "Hide call result" : "View full result"}
                      title={expandedCallId === call.id ? "Hide call result" : "View full result"}
                      onClick={() => setExpandedCallId(expandedCallId === call.id ? null : call.id)}
                    >
                      <ChevronDown size={17} className={`transition-transform ${expandedCallId === call.id ? "rotate-180" : ""}`} />
                    </Button>
                  </TableCell>
                </TableRow>
                {expandedCallId === call.id && (
                  <TableRow className="result-row">
                    <TableCell colSpan={6}>
                      <div className="result-panel">
                        <div className="flex items-center justify-between gap-3">
                          <div><p className="section-kicker">Call result</p><h4 className="font-semibold">{call.candidate.name}</h4></div>
                          {call.recording_url && <a className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline" href={call.recording_url} target="_blank" rel="noreferrer">Open recording <ExternalLink size={14} /></a>}
                        </div>
                        {call.result && Object.keys(call.result).length > 0 ? (
                          <dl className="result-grid">
                            {Object.entries(call.result).map(([key, value]) => (
                              <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{typeof value === "object" ? JSON.stringify(value) : String(value)}</dd></div>
                            ))}
                          </dl>
                        ) : <p className="text-sm text-muted-foreground">No extracted result is available yet.</p>}
                      </div>
                    </TableCell>
                  </TableRow>
                )}
                </Fragment>
              ))}
              {calls.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="empty-state">
                    <Radio size={18} /><span>No calls yet. Provision an agent and start screening to see live activity here.</span>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
