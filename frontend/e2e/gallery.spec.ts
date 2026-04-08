import { test, expect } from "@playwright/test";

test.describe("Gallery", () => {
  test("loads gallery page", async ({ page }) => {
    await page.goto("/gallery");
    
    // Should show some content
    await expect(page.locator("body")).toContainText(/gallery|build/i);
  });

  test("shows build cards if available", async ({ page }) => {
    await page.goto("/gallery");
    
    // Wait for page to load
    await page.waitForTimeout(1000);
    
    // Check for build cards or empty state
    const buildCards = page.locator("[data-testid='build-card'], article, .build-card");
    const emptyState = page.locator("text=/no builds|empty|get started/i");
    
    // Either we have build cards or an empty state
    const hasCards = (await buildCards.count()) > 0;
    const hasEmpty = (await emptyState.count()) > 0;
    
    expect(hasCards || hasEmpty).toBeTruthy();
  });
});
