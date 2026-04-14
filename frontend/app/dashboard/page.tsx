import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import ClientWrapper from "./ClientWrapper";

export default async function DashboardPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");
  return <ClientWrapper userId={userId} />;
}
