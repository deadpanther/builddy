import { getSession, getAccessToken } from "@auth0/nextjs-auth0";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    // Try to get the GitHub access token from Auth0 Token Vault
    let githubToken: string | undefined;
    try {
      const { accessToken } = await getAccessToken();
      githubToken = accessToken;
    } catch {
      // If Token Vault isn't configured, fall back to using the GitHub API without auth
      // This still works for public repos
    }

    const headers: Record<string, string> = {
      Accept: "application/vnd.github.v3+json",
      "User-Agent": "Builddy-Autopsy",
    };

    if (githubToken) {
      headers.Authorization = `Bearer ${githubToken}`;
    }

    // Fetch user's repos (or popular public repos if no token)
    const res = await fetch(
      "https://api.github.com/user/repos?sort=updated&per_page=30&type=all",
      { headers }
    );

    if (!res.ok) {
      // If user/repos fails (no GitHub token), return empty with a flag
      return NextResponse.json({
        repos: [],
        connected: false,
        message: "Connect your GitHub account via Auth0 to browse your repos",
      });
    }

    const repos = await res.json();

    return NextResponse.json({
      repos: repos.map((r: any) => ({
        id: r.id,
        name: r.name,
        full_name: r.full_name,
        html_url: r.html_url,
        description: r.description,
        language: r.language,
        stargazers_count: r.stargazers_count,
        updated_at: r.updated_at,
        private: r.private,
      })),
      connected: true,
    });
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to fetch repos", repos: [], connected: false },
      { status: 500 }
    );
  }
}
