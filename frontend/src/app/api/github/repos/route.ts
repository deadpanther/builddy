import { getSession } from "@auth0/nextjs-auth0";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json({ error: "Not authenticated", repos: [], connected: false }, { status: 401 });
    }

    // The user logged in via GitHub social connection.
    // Fetch the GitHub identity token from Auth0 Management API.
    const sub = session.user.sub; // e.g. "github|12345678"
    const isGitHub = sub?.startsWith("github|");

    if (!isGitHub) {
      return NextResponse.json({
        repos: [],
        connected: false,
        message: "Please sign in with GitHub to browse your repos",
      });
    }

    // Use Auth0 Management API to get the user's GitHub access token
    const domain = process.env.AUTH0_ISSUER_BASE_URL?.replace("https://", "") || process.env.AUTH0_DOMAIN;
    const clientId = process.env.AUTH0_CLIENT_ID;
    const clientSecret = process.env.AUTH0_CLIENT_SECRET;

    // Get a Management API token
    const tokenRes = await fetch(`https://${domain}/oauth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        grant_type: "client_credentials",
        client_id: clientId,
        client_secret: clientSecret,
        audience: `https://${domain}/api/v2/`,
      }),
    });

    let githubToken: string | undefined;

    if (tokenRes.ok) {
      const { access_token: mgmtToken } = await tokenRes.json();

      // Get the user's identities (includes GitHub access token)
      const userRes = await fetch(
        `https://${domain}/api/v2/users/${encodeURIComponent(sub)}?fields=identities`,
        { headers: { Authorization: `Bearer ${mgmtToken}` } }
      );

      if (userRes.ok) {
        const userData = await userRes.json();
        const ghIdentity = userData.identities?.find(
          (id: any) => id.provider === "github"
        );
        githubToken = ghIdentity?.access_token;
      }
    }

    if (!githubToken) {
      // Fallback: try fetching public repos using the GitHub username from Auth0
      const nickname = session.user.nickname;
      if (nickname) {
        const pubRes = await fetch(
          `https://api.github.com/users/${nickname}/repos?sort=updated&per_page=30`,
          { headers: { Accept: "application/vnd.github.v3+json", "User-Agent": "Builddy" } }
        );
        if (pubRes.ok) {
          const repos = await pubRes.json();
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
              private: false,
            })),
            connected: true,
            note: "Showing public repos only (enable Management API for private repos)",
          });
        }
      }

      return NextResponse.json({
        repos: [],
        connected: false,
        message: "Could not retrieve GitHub token. Enable Auth0 Management API access.",
      });
    }

    // Fetch repos using the GitHub access token
    const res = await fetch(
      "https://api.github.com/user/repos?sort=updated&per_page=30&type=all",
      {
        headers: {
          Accept: "application/vnd.github.v3+json",
          Authorization: `Bearer ${githubToken}`,
          "User-Agent": "Builddy",
        },
      }
    );

    if (!res.ok) {
      return NextResponse.json({
        repos: [],
        connected: false,
        message: "GitHub API request failed",
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
    console.error("GitHub repos error:", error);
    return NextResponse.json(
      { error: "Failed to fetch repos", repos: [], connected: false },
      { status: 500 }
    );
  }
}
