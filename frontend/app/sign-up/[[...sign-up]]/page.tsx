'use client';
import { SignUp } from '@clerk/nextjs';

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="bg-mesh" />
      <div className="relative z-10">
        <SignUp routing="path" path="/sign-up" />
      </div>
    </div>
  );
}
