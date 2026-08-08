"use client";

import { useRouter } from "next/navigation";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import StatusBadge from "../components/ui/StatusBadge";
import ThemeToggle from "../components/ThemeToggle";

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col relative">
      {/* Theme Toggle (Top Right) */}
      <div className="absolute top-4 right-4 sm:top-6 sm:right-6 z-10">
        <ThemeToggle />
      </div>

      {/* Hero Section */}
      <section className="flex flex-col items-center justify-center text-center px-4 py-24 sm:py-32 flex-1">
        <StatusBadge status="in_progress" />
        <h1 className="mt-6 text-4xl sm:text-6xl font-bold tracking-tight text-primary">
          Competency-Based Adaptive Assessments
        </h1>
        <p className="mt-4 max-w-2xl text-lg sm:text-xl text-muted-foreground">
          Unlock the power of dynamic, data-driven candidate evaluation. Scale your recruitment with precision and confidence.
        </p>
        <div className="mt-8 flex flex-col sm:flex-row gap-4">
          <Button variant="primary" onClick={() => router.push("/admin")}>
            Get Started
          </Button>
        </div>
      </section>

      {/* Statistics Section */}
      <section className="bg-subtle py-16 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="text-center flex flex-col items-center justify-center py-8">
              <span className="text-4xl font-bold text-accent">1,200+</span>
              <span className="mt-2 text-sm text-subtle-foreground font-medium uppercase tracking-wider">Competencies Verified</span>
            </Card>
            <Card className="text-center flex flex-col items-center justify-center py-8">
              <span className="text-4xl font-bold text-success">94%</span>
              <span className="mt-2 text-sm text-subtle-foreground font-medium uppercase tracking-wider">Confidence Convergence</span>
            </Card>
            <Card className="text-center flex flex-col items-center justify-center py-8">
              <span className="text-4xl font-bold text-primary">4</span>
              <span className="mt-2 text-sm text-subtle-foreground font-medium uppercase tracking-wider">Supported Formats</span>
            </Card>
          </div>
        </div>
      </section>

      {/* Feature Highlights */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-foreground">Core Capabilities</h2>
            <p className="mt-4 text-muted-foreground max-w-xl mx-auto">
              Everything you need to deliver world-class adaptive assessments at scale.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <Card className="flex flex-col">
              <h3 className="text-xl font-semibold text-primary">Bayesian Adaptive Engine</h3>
              <p className="mt-2 text-muted-foreground">
                Dynamically adjusts question difficulty and precisely estimates candidate ability with Bayesian models.
              </p>
            </Card>
            <Card className="flex flex-col">
              <h3 className="text-xl font-semibold text-primary">Automated Grading</h3>
              <p className="mt-2 text-muted-foreground">
                Instantly evaluates coding submissions, voice responses, and data analysis tasks without manual intervention.
              </p>
            </Card>
            <Card className="flex flex-col">
              <h3 className="text-xl font-semibold text-primary">Anti-Cheating Measures</h3>
              <p className="mt-2 text-muted-foreground">
                Maintains integrity through secure browser environments, identity verification, and behavior tracking.
              </p>
            </Card>
          </div>
        </div>
      </section>
    </div>
  );
}
