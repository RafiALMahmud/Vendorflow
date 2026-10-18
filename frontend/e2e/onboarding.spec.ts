import { test, expect, type Page, type Browser } from '@playwright/test';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

const api = 'http://localhost:8000/api/v1';
const fixtures = path.resolve('../backend/tests/fixtures/vendorflow_qa');
const manifest = JSON.parse(readFileSync(path.join(fixtures, 'expected_results.json'), 'utf8')) as {
  documents: { file: string; type: string; expected: Record<string, string> }[];
};
let positive: { documentId: string; applicationId: string };
const runtimeErrors: string[] = [];

async function signin(page: Page, credentials: { email: string; password: string }) {
  await page.goto('/login');
  page.on('pageerror', error => runtimeErrors.push(error.message));
  await page.getByLabel('Email', { exact: true }).fill(credentials.email);
  await page.getByLabel('Password', { exact: true }).fill(credentials.password);
  const response = page.waitForResponse(r => r.url().endsWith('/auth/login') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const body = await (await response).json();
  await page.waitForURL(/\/(dashboard|admin)$/);
  return body.access_token as string;
}

async function vendor(page: Page, registration: string) {
  const credentials = { email: `qa-vendor-${randomUUID()}@example.com`, password: `Qa-${randomUUID()}` };
  await page.goto('/register');
  await page.getByLabel('Full name', { exact: true }).fill('Fictional QA Vendor');
  await page.getByLabel('Email', { exact: true }).fill(credentials.email);
  await page.getByLabel('Password', { exact: true }).fill(credentials.password);
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await page.waitForURL('**/login');
  const token = await signin(page, credentials);
  await page.getByRole('link', { name: 'Company profile', exact: true }).click();
  for (const [label, value] of Object.entries({ 'Company name': 'NORTHSTAR TRADING LTD',
    'Registration number': registration, 'Contact email': credentials.email, Phone: '+8801700000000', Address: '1 Fictional QA Road, Dhaka' })) {
    await page.getByLabel(label, { exact: true }).fill(value);
  }
  await page.getByRole('button', { name: 'Create profile', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Save changes', exact: true })).toBeVisible();
  await page.getByLabel('Phone', { exact: true }).fill('+8801711111111');
  const saved = page.waitForResponse(r => r.url().endsWith('/vendors/me') && r.request().method() === 'PATCH');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  expect((await saved).status()).toBe(200);
  return token;
}

async function upload(page: Page, token: string, item: typeof manifest.documents[number]) {
  await page.getByRole('link', { name: 'Documents', exact: true }).click();
  await page.getByRole('combobox', { name: 'Document type', exact: true }).selectOption(item.type);
  await page.getByLabel('File', { exact: true }).setInputFiles(path.join(fixtures, item.file));
  const uploaded = page.waitForResponse(r => r.url().endsWith('/documents/upload') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Upload document', exact: true }).click();
  const response = await uploaded;
  expect(response.status()).toBe(201);
  const document = await response.json();
  expect(document.processing_status).toBe('processed');
  const fields = await (await page.request.get(`${api}/documents/${document.id}/extracted-fields`, {
    headers: { Authorization: `Bearer ${token}` },
  })).json() as { field_name: string; raw_value: string; normalized_value: string | null; review_status: string; extraction_method: string }[];
  expect(Object.fromEntries(fields.map(field => [field.field_name, field.normalized_value || field.raw_value]))).toEqual(item.expected);
  expect(fields.every(field => field.review_status === 'unreviewed')).toBe(true);
  expect(fields.every(field => field.extraction_method === (item.file.startsWith('04') ? 'tesseract_ocr' : 'pdf_text'))).toBe(true);
  return document.id as string;
}

async function confirmFields(page: Page, filename: string, fields: Record<string, string>) {
  const row = page.getByRole('listitem').filter({ hasText: filename });
  await row.getByRole('link', { name: 'Review extraction', exact: true }).click();
  for (const [name, value] of Object.entries(fields)) {
    const input = page.locator(`#field-${name}`);
    await expect(input).toHaveValue(value);
    const item = page.getByRole('listitem').filter({ has: input });
    await item.getByRole('button', { name: 'Confirm extracted value', exact: true }).click();
    await expect(item.getByText('confirmed', { exact: true })).toBeVisible();
  }
}

async function submit(page: Page) {
  await page.getByRole('link', { name: 'Applications', exact: true }).click();
  await page.getByRole('button', { name: 'Create application draft' }).click();
  const response = page.waitForResponse(r => r.url().endsWith('/submit') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Submit application', exact: true }).click();
  const body = await (await response).json();
  await expect(page.getByRole('heading', { name: 'Application status: submitted' })).toBeVisible();
  return body.id as string;
}

async function admin(browser: Browser) {
  const page = await browser.newPage();
  const credentials = JSON.parse(readFileSync(path.resolve('../.local/browser-qa.json'), 'utf8'));
  return { page, token: await signin(page, credentials) };
}

async function openCase(page: Page, id: string) {
  await page.locator(`tr[data-application-id="${id}"]`).getByRole('button').click();
  await expect(page.getByRole('heading', { name: 'NORTHSTAR TRADING LTD', exact: true })).toBeVisible();
}

async function decide(page: Page, button: string, note: string) {
  await page.getByRole('textbox', { name: /Review note/ }).fill(note);
  await page.getByRole('button', { name: button, exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', { name: 'Confirm decision', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
}

test.describe.serial('Release kit against real PostgreSQL, API, browser and OCR', () => {
  test('positive PDFs: register through approval with corrected fields and audit', async ({ page, browser }, testInfo) => {
    const token = await vendor(page, 'REG-2026-0042');
    let firstDocument = '';
    for (const item of manifest.documents.slice(0, 3)) {
      const id = await upload(page, token, item);
      firstDocument ||= id;
      await confirmFields(page, item.file, item.expected);
    }
    const id = await submit(page);
    positive = { documentId: firstDocument, applicationId: id };
    const reviewer = await admin(browser);
    await openCase(reviewer.page, id);
    await expect(reviewer.page.getByText(/Readiness: 100\/100/)).toBeVisible();
    await reviewer.page.getByRole('button', { name: 'Approve', exact: true }).click();
    await expect(reviewer.page.getByRole('dialog')).toBeVisible();
    await reviewer.page.keyboard.press('Escape');
    await expect(reviewer.page.getByRole('dialog')).not.toBeVisible();
    await expect(reviewer.page.getByText('Status: submitted', { exact: true })).toBeVisible();
    const download = reviewer.page.waitForEvent('download');
    await reviewer.page.getByRole('button', { name: 'Download trade license', exact: true }).click();
    expect(readFileSync((await (await download).path())!).subarray(0, 4).toString()).toBe('%PDF');
    await decide(reviewer.page, 'Request corrections', 'Please correct the registration field for this fictional demo.');
    await expect(reviewer.page.getByText('Status: needs correction', { exact: true })).toBeVisible();
    await page.getByRole('link', { name: 'Dashboard', exact: true }).click();
    await page.getByRole('link', { name: 'Applications', exact: true }).click();
    await expect(page.getByText(/Reviewer note: Please correct/)).toBeVisible();
    await page.getByRole('link', { name: 'Documents', exact: true }).click();
    await page.getByRole('listitem').filter({ hasText: manifest.documents[0].file }).getByRole('link', { name: 'Review extraction' }).click();
    const registration = page.locator('#field-registration_number');
    await registration.fill('REG-2026-0042-REVIEWED');
    await page.getByRole('listitem').filter({ has: registration }).getByRole('button', { name: 'Save correction', exact: true }).click();
    await expect(page.getByRole('listitem').filter({ has: registration }).getByText('corrected', { exact: true })).toBeVisible();
    await page.getByRole('link', { name: 'Applications', exact: true }).click();
    await page.getByRole('button', { name: 'Resubmit application', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Application status: resubmitted' })).toBeVisible();
    await reviewer.page.getByRole('button', { name: 'Reload case' }).click();
    await expect(reviewer.page.getByText('Status: resubmitted', { exact: true })).toBeVisible();
    await expect(reviewer.page.getByText(/REG-2026-0042-REVIEWED/)).toBeVisible();
    await decide(reviewer.page, 'Approve', 'Verified fictional documents reviewed by a human.');
    await expect(reviewer.page.getByText('Status: approved', { exact: true })).toBeVisible();
    const detail = await (await reviewer.page.request.get(`${api}/admin/applications/${id}`, { headers: { Authorization: `Bearer ${reviewer.token}` } })).json();
    expect(detail.audit_events.map((event: { action: string }) => event.action)).toEqual(['draft_created', 'submitted', 'needs_correction', 'resubmitted', 'approved']);
    await reviewer.page.screenshot({ path: testInfo.outputPath('admin-approved-desktop.png'), fullPage: true });
    await reviewer.page.setViewportSize({ width: 390, height: 844 });
    expect(await reviewer.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await reviewer.page.screenshot({ path: testInfo.outputPath('admin-approved-mobile.png'), fullPage: true });
    await page.getByRole('link', { name: 'Dashboard', exact: true }).click();
    await page.getByRole('link', { name: 'Applications', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Application status: approved' })).toBeVisible();
    await reviewer.page.close();
    expect(runtimeErrors).toEqual([]);
  });

  test('real scanned PDF: unverified safeguards, expired/mismatch findings, rejection and isolation', async ({ page, browser }, testInfo) => {
    const token = await vendor(page, 'REG-2026-0099');
    const item = manifest.documents[3];
    await upload(page, token, item);
    const id = await submit(page);
    const reviewer = await admin(browser);
    await openCase(reviewer.page, id);
    const requestHeaders = { Authorization: `Bearer ${reviewer.token}` };
    const rawRisk = await (await reviewer.page.request.get(`${api}/admin/applications/${id}/risk`, { headers: requestHeaders })).json();
    expect(rawRisk.findings.some((finding: { code: string }) => ['expired_license', 'confirmed_company_name_mismatch'].includes(finding.code))).toBe(false);
    await decide(reviewer.page, 'Request corrections', 'Please verify the scanned document fields.');
    await page.getByRole('link', { name: 'Documents', exact: true }).click();
    await confirmFields(page, item.file, item.expected);
    await page.getByRole('link', { name: 'Applications', exact: true }).click();
    await page.getByRole('button', { name: 'Resubmit application', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Application status: resubmitted' })).toBeVisible();
    await reviewer.page.getByRole('button', { name: 'Reload case' }).click();
    await expect(reviewer.page.getByText(/Readiness: 25\/100/)).toBeVisible();
    const risk = await (await reviewer.page.request.get(`${api}/admin/applications/${id}/risk`, { headers: requestHeaders })).json();
    expect(risk.findings.map((finding: { code: string }) => finding.code).sort()).toEqual(['confirmed_company_name_mismatch', 'expired_license', 'missing_required_document']);
    await expect(reviewer.page.getByText('Status: resubmitted', { exact: true })).toBeVisible();
    await reviewer.page.screenshot({ path: testInfo.outputPath('negative-findings.png'), fullPage: true });
    await decide(reviewer.page, 'Reject', 'Expired and inconsistent fictional evidence requires replacement.');
    await expect(reviewer.page.getByText('Status: rejected', { exact: true })).toBeVisible();
    for (const endpoint of [`/documents/${positive.documentId}`, `/documents/${positive.documentId}/file`, `/documents/${positive.documentId}/extracted-fields`]) {
      expect((await page.request.get(api + endpoint, { headers: { Authorization: `Bearer ${token}` } })).status()).toBe(404);
    }
    expect((await page.request.post(`${api}/applications/${positive.applicationId}/submit`, { headers: { Authorization: `Bearer ${token}` } })).status()).toBe(404);
    expect((await page.request.get(`${api}/admin/dashboard`, { headers: { Authorization: `Bearer ${token}` } })).status()).toBe(403);
    await page.getByRole('link', { name: 'Dashboard', exact: true }).click();
    await page.getByRole('link', { name: 'Applications', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Application status: rejected' })).toBeVisible();
    await page.getByRole('button', { name: 'Log out', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
    await reviewer.page.close();
    expect(runtimeErrors).toEqual([]);
  });
});
