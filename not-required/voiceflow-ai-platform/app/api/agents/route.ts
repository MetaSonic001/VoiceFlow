import { NextResponse } from "next/server";

const DEMO_TENANT = "demo-tenant";
const DEMO_USER = "demo-user";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const page = Math.max(1, Number(url.searchParams.get("page")) || 1);
  const limit = Math.min(200, Math.max(1, Number(url.searchParams.get("limit")) || 20));
  const search = url.searchParams.get("search") || "";
  const status = url.searchParams.get("status") || "";

  try {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    const backendReqUrl = new URL(`${backendUrl.replace(/\/$/, "")}/api/agents`);
    backendReqUrl.searchParams.set("page", String(page));
    backendReqUrl.searchParams.set("limit", String(limit));
    if (search) backendReqUrl.searchParams.set("search", search);
    if (status) backendReqUrl.searchParams.set("status", status);

    const r = await fetch(backendReqUrl.toString(), {
      headers: {
        "x-tenant-id": DEMO_TENANT,
        "x-user-id": DEMO_USER,
      },
    });

    if (r.ok) {
      return NextResponse.json(await r.json());
    } else {
      console.error("Backend agents request failed:", r.status, await r.text());
      return NextResponse.json({ agents: [], total: 0, page, limit });
    }
  } catch (err) {
    console.error("Failed to fetch agents:", err);
    return NextResponse.json({ agents: [], total: 0, page, limit });
  }
}
