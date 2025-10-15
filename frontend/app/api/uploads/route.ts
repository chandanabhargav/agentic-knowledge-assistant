import { NextResponse } from "next/server";
const API = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000/api' as string;
console.log(API, "API");
export async function GET() {
  const r = await fetch(`${API}/api/uploads`, {
    headers: { Authorization: `Bearer ${process.env.NEXT_PUBLIC_BEARER_TOKEN || ""}` },
    cache: "no-store",
  });
  const data = await r.json();
  return NextResponse.json(data, { status: r.status });
}
