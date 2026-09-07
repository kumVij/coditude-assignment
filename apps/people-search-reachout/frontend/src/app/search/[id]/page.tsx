"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, type ReachoutCall, type Search } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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

export default function SearchDetailPage() {
  const params = useParams<{ id: string }>();
  const searchId = params.id;

  const [search, setSearch] = useState<Search | null>(null);
  const [calls, setCalls] = useState<ReachoutCall[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    try {
      const [s, c] = await Promise.all([api.getSearch(searchId), api.listCalls(searchId)]);
      setSearch(s);
      setCalls(c);
    } catch (e) {
      setError(String(e));
    }
  }, [searchId]);

  useEffect(() => {
    loadAll();
    const interval = setInterval(async () => {
      try {
        setCalls(await api.listCalls(searchId, true));
      } catch {
        /* ignore transient polling errors */
      }
    }, 8000);
    return () => clearInterval(interval);
  }, [searchId, loadAll]);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleProvision = async () => {
    setBusy("provision");
    setError(null);
    try {
      setSearch(await api.provisionAgent(searchId));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const handleReachout = async () => {
    setBusy("reachout");
    setError(null);
    try {
      await api.startReachout(searchId, Array.from(selected));
      setSelected(new Set());
      setCalls(await api.listCalls(searchId));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  if (!search) {
    return <p className="text-sm text-muted-foreground">Loading...</p>;
  }

  return (
    <main className="flex flex-col gap-8">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{search.job_title}</h1>
          <p className="max-w-2xl text-sm text-muted-foreground">{search.job_description}</p>
          <div className="mt-2 flex flex-wrap gap-1">
            {search.parsed_titles.map((t) => (
              <Badge key={t} variant="outline">
                {t}
              </Badge>
            ))}
            {search.parsed_skills.map((s) => (
              <Badge key={s} variant="secondary">
                {s}
              </Badge>
            ))}
          </div>
        </div>
        <Badge variant={search.hunar_agent_id ? "success" : "outline"}>
          {search.hunar_agent_id ? "Agent ready" : "Agent not provisioned"}
        </Badge>
      </header>

      {error && (
        <p className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </p>
      )}

      {!search.hunar_agent_id && (
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <p className="text-sm">Provision the Hunar voice agent before reaching out to candidates.</p>
            <Button onClick={handleProvision} disabled={busy === "provision"}>
              {busy === "provision" ? "Provisioning..." : "Provision agent"}
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Sourced candidates ({search.candidates.length})</CardTitle>
          <Button
            onClick={handleReachout}
            disabled={!search.hunar_agent_id || selected.size === 0 || busy === "reachout"}
          >
            {busy === "reachout" ? "Calling..." : `Reach out to ${selected.size} selected`}
          </Button>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead />
                <TableHead>Name</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Location</TableHead>
                <TableHead>Phone</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {search.candidates.map((c) => (
                <TableRow key={c.id}>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={selected.has(c.id)}
                      onChange={() => toggle(c.id)}
                      disabled={!c.mobile_number}
                    />
                  </TableCell>
                  <TableCell>
                    <a
                      className="text-primary underline underline-offset-2"
                      href={c.linkedin_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {c.full_name}
                    </a>
                  </TableCell>
                  <TableCell>{c.job_title}</TableCell>
                  <TableCell>{c.company}</TableCell>
                  <TableCell>{c.location}</TableCell>
                  <TableCell>{c.mobile_number || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Reachout calls</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Candidate</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Recommendation</TableHead>
                <TableHead>Recording</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {calls.map((call) => (
                <TableRow key={call.id}>
                  <TableCell>{call.candidate.full_name}</TableCell>
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
                        className="text-primary underline underline-offset-2"
                        href={call.recording_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Listen
                      </a>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {calls.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-muted-foreground">
                    No reachout calls yet.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </main>
  );
}
