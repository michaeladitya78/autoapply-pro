import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import dynamic from "next/dynamic";

// Bug 3 fix: disable SSR on DashboardClient to prevent hydration mismatches
// from WebSocket, date-fns format calls, and real-time state initialization.
const DashboardClient = dynamic(() => import("./DashboardClient"), { ssr: false });

export default async function DashboardPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");
  return <DashboardClient userId={userId} />;
}
