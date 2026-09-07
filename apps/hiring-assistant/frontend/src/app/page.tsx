"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Job } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";

export default function HomePage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [mustHave, setMustHave] = useState("");
  const [questions, setQuestions] = useState("");

  const refresh = () => {
    setLoading(true);
    api
      .listJobs()
      .then(setJobs)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(refresh, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await api.createJob({
        title,
        description,
        must_have_skills: mustHave,
        screening_questions: questions,
      });
      setTitle("");
      setDescription("");
      setMustHave("");
      setQuestions("");
      refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setCreating(false);
    }
  };

  return (
    <main className="flex flex-col gap-8">
      <header>
        <h1 className="text-2xl font-bold">AI Hiring Assistant</h1>
        <p className="text-sm text-muted-foreground">
          Create a role, add candidates, and let a Hunar voice agent conduct the initial phone screen.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>New job</CardTitle>
          <CardDescription>This creates the role. You&apos;ll provision its voice agent next.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={handleCreate}>
            <div className="grid gap-1.5">
              <Label htmlFor="title">Job title</Label>
              <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} required />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="description">Job description</Label>
              <Textarea
                id="description"
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                required
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="mustHave">Must-have skills (free text)</Label>
              <Input id="mustHave" value={mustHave} onChange={(e) => setMustHave(e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="questions">Screening questions (one per line, optional)</Label>
              <Textarea
                id="questions"
                rows={3}
                placeholder={"What is your notice period?\nWhat is your expected CTC?"}
                value={questions}
                onChange={(e) => setQuestions(e.target.value)}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" disabled={creating}>
              {creating ? "Creating..." : "Create job"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Jobs</h2>
        {loading && <p className="text-sm text-muted-foreground">Loading...</p>}
        {!loading && jobs.length === 0 && (
          <p className="text-sm text-muted-foreground">No jobs yet — create one above.</p>
        )}
        <div className="grid gap-3">
          {jobs.map((job) => (
            <Link key={job.id} href={`/jobs/${job.id}`}>
              <Card className="transition-shadow hover:shadow-md">
                <CardContent className="flex items-center justify-between p-4">
                  <div>
                    <p className="font-medium">{job.title}</p>
                    <p className="line-clamp-1 text-sm text-muted-foreground">{job.description}</p>
                  </div>
                  <Badge variant={job.hunar_agent_id ? "success" : "outline"}>
                    {job.hunar_agent_id ? "Agent ready" : "Agent not provisioned"}
                  </Badge>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
