import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

export async function GET(req: Request) {
  const { userId, orgId, getToken } = await auth();

  if (!userId) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  // ✅ get Clerk JWT
const token = await getToken()
  // Query params
  const url = new URL(req.url);
  const page = Math.max(1, Number(url.searchParams.get("page")) || 1);
  const limit = Math.min(
    200,
    Math.max(1, Number(url.searchParams.get("limit")) || 20),
  );
  const search = url.searchParams.get("search") || "";
  const status = url.searchParams.get("status") || "";

  try {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

    const backendReqUrl = new URL(
      `${backendUrl.replace(/\/$/, "")}/api/agents`,
    );
    backendReqUrl.searchParams.set("page", String(page));
    backendReqUrl.searchParams.set("limit", String(limit));

    const backendKey = process.env.BACKEND_API_KEY || "";
    if (search) backendReqUrl.searchParams.set("search", search);
    if (status) backendReqUrl.searchParams.set("status", status);

    const r = await fetch(backendReqUrl.toString(), {
      headers: {
        Authorization: `Bearer ${token}`,
        "X-API-Key": backendKey,
        "x-tenant-id": orgId || userId || "default-tenant",
        "x-user-id": userId,
      },
    });

    if (r.ok) {
      const data = await r.json();
      return NextResponse.json(data);
    } else {
      console.error(
        "New backend agents request failed:",
        r.status,
        await r.text(),
      );
      return NextResponse.json({ agents: [], total: 0, page, limit });
    }
  } catch (err) {
    console.error("Failed to fetch agents from new backend:", err);
    return NextResponse.json({ agents: [], total: 0, page, limit });
  }
}
