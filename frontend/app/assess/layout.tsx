import CandidateNav from "@/components/CandidateNav";

export default function AssessLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <CandidateNav />
      {children}
    </>
  );
}