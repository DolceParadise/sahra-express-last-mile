import { test, expect, type Page, type Locator } from "@playwright/test";
async function choose(page: Page, control: Locator, value: string) {
  await control.click();
  await page.locator('[role="option"][data-value="' + value + '"]').click();
}
const artifact = (name: string) =>
  new URL("../../outputs/" + name, import.meta.url).pathname;
test("Manager generates, inspects, edits, repairs, approves and exports a real plan", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Morning overview" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Generate plan", exact: true })
    .click();
  await expect(page.getByText(/Version \d+ saved/)).toBeVisible();
  await page.screenshot({ path: artifact("overview.png"), fullPage: true });
  await page.getByRole("button", { name: /Address review/ }).click();
  await choose(page, page.getByLabel("Address quality"), "AMBIGUOUS");
  await page.locator(".address-list button").first().click();
  await expect(
    page.getByRole("heading", { name: "Record a verified correction" }),
  ).toBeVisible();
  await expect(page.locator(".review-detail .callout")).toContainText(
    /History|Multiple/,
  );
  await expect(page.getByLabel("Latitude", { exact: true })).toHaveValue("");
  await page.getByRole("button", { name: /Route planning/ }).click();
  await choose(
    page,
    page.getByRole("combobox", { name: "Route", exact: true }),
    "R01",
  );
  await expect(page.locator(".leaflet-container")).toBeVisible();
  await expect(page.locator(".route-detail .stops li").first()).toBeVisible();
  await page.screenshot({ path: artifact("routes.png"), fullPage: true });
  await page.getByRole("button", { name: /Edit & validate/ }).click();
  const form = page.locator("form").first();
  await choose(
    page,
    form.getByRole("combobox", { name: "Change", exact: true }),
    "vehicle",
  );
  await choose(
    page,
    form.getByRole("combobox", { name: "Resource", exact: true }),
    "V02",
  );
  await form
    .getByLabel("Reason", { exact: true })
    .fill("Deliberate chilled-to-bike assignment for validation demo");
  await form.getByRole("button", { name: "Apply and validate" }).click();
  await expect(page.getByRole("status")).toContainText("hard violations");
  await expect(page.locator(".finding.hard").first()).toBeVisible();
  await page.screenshot({
    path: artifact("invalid-assignment.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: /Approval & export/ }).click();
  await expect(
    page.getByRole("button", { name: "Approve version" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: /Edit & validate/ }).click();
  await choose(
    page,
    page
      .locator("form")
      .getByRole("combobox", { name: "Resource", exact: true }),
    "V17",
  );
  await page
    .locator("form")
    .getByLabel("Reason", { exact: true })
    .fill("Restore original chilled van");
  await page.getByRole("button", { name: "Apply and validate" }).click();
  await expect(page.getByRole("status")).toContainText("No hard violations");
  await page.getByRole("button", { name: /Approval & export/ }).click();
  await page.getByRole("button", { name: "Approve version" }).click();
  await expect(page.locator(".workflow .current")).toHaveText("APPROVED");
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: /Download Appendix B/ }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/sahra-plan-v\d+.json/);
  expect(errors).toEqual([]);
});
test("Mobile overview remains navigable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Morning overview" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Input audit/ }).click();
  await expect(
    page.getByRole("heading", { name: "Input audit" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("Map outage and pre-dispatch driver absence keep a usable partial plan", async ({
  page,
}) => {
  await page.route("**/*.tile.openstreetmap.org/**", (route) => route.abort());
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Morning overview" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Generate plan", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("No hard violations");
  await page.getByRole("button", { name: /Route planning/ }).click();
  await expect(page.getByText(/Map tiles unavailable/)).toBeVisible();
  await expect(page.locator(".route-detail .stops li").first()).toBeVisible();
  const before = await page.request.get("/api/versions");
  const version = (await before.json())[0].version;
  const previous = await (
    await page.request.get("/api/plans/" + version)
  ).json();
  await page.getByRole("button", { name: /Operational exceptions/ }).click();
  await choose(
    page,
    page.getByRole("combobox", { name: "Resource", exact: true }),
    previous.routes[0].driver_id,
  );
  await page
    .getByRole("textbox", { name: "Reason", exact: true })
    .fill("Simulated absence for browser verification");
  await page.getByRole("button", { name: "Apply simulated event" }).click();
  await expect(page.getByRole("status")).toContainText("No hard violations");
  await expect(page.getByText(/Routes affected: R01/)).toBeVisible();
  const versions = await (await page.request.get("/api/versions")).json();
  const after = await (
    await page.request.get("/api/plans/" + versions[0].version)
  ).json();
  expect(after.routes.length).toBe(previous.routes.length - 1);
  expect(after.unassigned.length).toBeGreaterThan(previous.unassigned.length);
  expect(after.routes).toEqual(previous.routes.slice(1));
});

test("Coss selects support the keyboard and evidence dialogs restore focus", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Morning overview" }),
  ).toBeVisible();
  const guide = page.getByRole("button", {
    name: "Planning guide",
    exact: true,
  });
  await guide.click();
  const dialog = page.getByRole("dialog");
  await expect(
    dialog.getByRole("heading", { name: "Planning guide" }),
  ).toBeVisible();
  await page.keyboard.press("Tab");
  expect(
    await dialog.evaluate((node) => node.contains(document.activeElement)),
  ).toBe(true);
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(guide).toBeFocused();
  await page.getByRole("button", { name: /Address review/ }).click();
  const quality = page.getByRole("combobox", { name: "Address quality" });
  await quality.focus();
  await quality.press("ArrowDown");
  await expect(page.getByRole("listbox")).toBeVisible();
  await expect(
    page.getByRole("option", { name: "ALL", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("End");
  await expect(
    page.getByRole("option", { name: "INVALID", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(quality).toContainText("INVALID");
  await expect(page.locator(".address-list button")).toHaveCount(27);
  await page.locator(".address-list button").first().click();
  await page
    .getByRole("button", { name: /Parsed components, candidates/ })
    .click();
  await expect(
    page
      .getByRole("dialog")
      .getByRole("heading", { name: /Parsed components/ }),
  ).toBeVisible();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Close", exact: true })
    .last()
    .click();
  await expect(page.getByRole("dialog")).toBeHidden();
  expect(errors).toEqual([]);
});

test("Coss fields keep an incomplete address confirmation from reaching the API", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Morning overview" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Address review/ }).click();
  await choose(
    page,
    page.getByRole("combobox", { name: "Address quality" }),
    "AMBIGUOUS",
  );
  await page.locator(".address-list button").first().click();
  await page
    .getByLabel("Evidence / reason", { exact: true })
    .fill("Checking the required coordinates");
  let submitted = false;
  page.on("request", (request) => {
    if (
      request.method() === "POST" &&
      request.url().includes("/address-review")
    )
      submitted = true;
  });
  await page
    .getByRole("button", { name: "Confirm location", exact: true })
    .click();
  await expect(page.getByLabel("Latitude", { exact: true })).toBeFocused();
  expect(submitted).toBe(false);
});

test("All seven screens and the evidence dialog fit a mobile viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Morning overview" }),
  ).toBeVisible();
  for (const name of [
    "Morning overview",
    "Input audit",
    "Address review",
    "Route planning",
    "Edit & validate",
    "Approval & export",
    "Operational exceptions",
  ]) {
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("button", { name: new RegExp(name.replace("&", "&")) })
      .click();
    await expect(
      page.getByRole("heading", { name, exact: true }),
    ).toBeVisible();
    if (name === "Address review")
      await page.locator(".address-list button").first().click();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
      name,
    ).toBe(true);
  }
  await page
    .getByRole("navigation")
    .getByRole("button", { name: /Input audit/ })
    .click();
  await page
    .getByRole("button", {
      name: "Raw input values and row dispositions",
      exact: true,
    })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  // The coss mobile popup enters from below. Measure its settled position.
  await expect.poll(async () => {
    const bounds = await page.getByRole("dialog").boundingBox();
    return bounds ? bounds.y + bounds.height : Infinity;
  }).toBeLessThanOrEqual(845);
  const box = await page.getByRole("dialog").boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  expect(box!.y).toBeGreaterThanOrEqual(0);
  expect(box!.y + box!.height).toBeLessThanOrEqual(845);
  await expect(page.getByRole("dialog").getByRole("button", {name: "Close", exact: true}).last()).toBeInViewport({ratio: 1});
  await page.screenshot({
    path: artifact("coss-mobile-dialog.png"),
    fullPage: false,
  });
});
