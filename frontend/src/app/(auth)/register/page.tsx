"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function RegisterPage() {
  const router = useRouter();
  useEffect(() => { router.replace("/"); }, []);
  return null;
}

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register(form.name, form.email, form.password);
      setRegistered(true);
      toast.success("Account created!");
      setTimeout(() => router.push("/dashboard"), 2000);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="absolute inset-0 bg-gradient-radial from-neon-blue/5 via-transparent to-transparent" />
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md relative z-10">
        <div className="glass-card">
          <div className="flex items-center gap-2 mb-8">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-green to-neon-blue flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-black" />
            </div>
            <span className="font-bold text-xl gradient-text">TradeMind AI</span>
          </div>

          {registered ? (
            <div className="text-center py-4">
              <div className="w-16 h-16 rounded-full bg-neon-green/20 flex items-center justify-center mx-auto mb-4">
                <Mail className="w-8 h-8 text-neon-green" />
              </div>
              <h2 className="text-xl font-bold mb-2">Check your email</h2>
              <p className="text-muted-foreground text-sm">
                We sent a verification link to <span className="text-foreground font-medium">{form.email}</span>.
              </p>
              <p className="text-xs text-muted-foreground mt-4">Redirecting to dashboard...</p>
            </div>
          ) : (
            <>
              <h1 className="text-2xl font-bold mb-2">Create your account</h1>
              <p className="text-muted-foreground text-sm mb-6">Start trading with AI-powered insights</p>

              <form onSubmit={handleSubmit} className="space-y-4">
                {[
                  { label: "Full Name", key: "name", type: "text", placeholder: "John Doe" },
                  { label: "Email", key: "email", type: "email", placeholder: "you@example.com" },
                ].map(({ label, key, type, placeholder }) => (
                  <div key={key}>
                    <label className="text-sm font-medium mb-1.5 block">{label}</label>
                    <input
                      type={type} value={form[key as keyof typeof form]}
                      onChange={(e) => setForm({ ...form, [key]: e.target.value })} required
                      className="w-full bg-muted border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50 transition-all"
                      placeholder={placeholder}
                    />
                  </div>
                ))}
                <div>
                  <label className="text-sm font-medium mb-1.5 block">Password</label>
                  <div className="relative">
                    <input
                      type={showPass ? "text" : "password"} value={form.password}
                      onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={8}
                      className="w-full bg-muted border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neon-green/50 transition-all pr-10"
                      placeholder="Min 8 characters"
                    />
                    <button type="button" onClick={() => setShowPass(!showPass)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                      {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
                  {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                  {loading ? "Creating account..." : "Create Free Account"}
                </button>
              </form>

              <p className="text-center text-sm text-muted-foreground mt-6">
                Already have an account?{" "}
                <Link href="/login" className="text-neon-green hover:underline font-medium">Sign in</Link>
              </p>
            </>
          )}
        </div>
      </motion.div>
    </div>
  );
}
