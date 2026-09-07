"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, type Search } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";

export default function HomePage() {
  const router = useRouter();
  const [searches, setSearches] = useState<Search[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [jobTitle, setJobTitle] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [location, setLocation] = useState("");

  useEffect(() => {
    api
      .listSearches()
      .then(setSearches)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const search = await api.createSearch({
        job_title: jobTitle,
        job_description: jobDescription,
        location_query: location,
      });
      router.push(`/search/${search.id}`);
    } catch (e) {
      setError(String(e));
      setSubmitting(false);
    }
  };

  return (
    <main className="flex flex-col gap-8">
      <header>
        <h1 className="text-2xl font-bold">People Search &amp; Reachout</h1>
        <p className="text-sm text-muted-foreground">
          Paste a job description, source matching candidates, and let a Hunar voice agent do the
          first outreach call.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Paste a job description</CardTitle>
          <CardDescription>
            We&apos;ll extract search keywords and look up matching people automatically.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <div className="grid gap-1.5">
              <Label htmlFor="jobTitle">Job title</Label>
              <Input id="jobTitle" value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} required />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="jobDescription">Job description</Label>
              <Textarea
                id="jobDescription"
                rows={6}
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                required
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="location">Location (optional)</Label>
              <Input
                id="location"
                placeholder="e.g. Bengaluru, India"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" disabled={submitting}>
              {submitting ? "Searching..." : "Search for candidates"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Past searches</h2>
        {loading && <p className="text-sm text-muted-foreground">Loading...</p>}
        {!loading && searches.length === 0 && (
          <p className="text-sm text-muted-foreground">No searches yet — try one above.</p>
        )}
        <div className="grid gap-3">
          {searches.map((s) => (
            <Link key={s.id} href={`/search/${s.id}`}>
              <Card className="transition-shadow hover:shadow-md">
                <CardContent className="flex items-center justify-between p-4">
                  <div>
                    <p className="font-medium">{s.job_title}</p>
                    <p className="text-sm text-muted-foreground">
                      {s.candidates.length} candidates sourced{s.location_query ? ` in ${s.location_query}` : ""}
                    </p>
                  </div>
                  <Badge variant={s.hunar_agent_id ? "success" : "outline"}>
                    {s.hunar_agent_id ? "Agent ready" : "Agent not provisioned"}
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
