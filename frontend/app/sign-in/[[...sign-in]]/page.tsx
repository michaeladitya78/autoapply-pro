'use client';
import { SignIn } from '@clerk/nextjs';

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="bg-mesh" />
      <div className="relative z-10">
        <SignIn routing="path" path="/sign-in" />
      </div>
    </div>
  );
}
