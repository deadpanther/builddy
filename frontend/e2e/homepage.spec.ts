import { test, expect } from "@playwright/test";

test.describe("Homepage", () => {
  test("loads successfully", async ({ page }) => {
    await page.goto("/");
    
    // Should show the main heading
    await expect(page.locator("h1")).toContainText(/build|create|app/i);
  });

  test("shows build input form", async ({ page }) => {
    await page.goto("/");
    
    // Should have a textarea or input for prompts
    const promptInput = page.locator("textarea").first();
    await expect(promptInput).toBeVisible();
  });

  test("navigation works", async ({ page }) => {
    await page.goto("/");
    
    // Check for navigation links
    const galleryLink = page.locator("a[href*='gallery']");
    if (await galleryLink.count() > 0) {
      await galleryLink.first().click();
      await expect(page).toHaveURL(/gallery/);
    }
  });
});
