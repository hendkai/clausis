// Firefox profile pre-seed for the Clausis browser AT-SPI session test.
// Copied into the throwaway profile before launch so the window shows the
// local file:// probe page and nothing else: no default-browser prompt,
// no welcome tour, no telemetry consent ping, no update checks.
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.aboutwelcome.enabled", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("app.update.enabled", false);
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", false);
// The page is German while the UI locale is en-US: without these prefs
// Firefox offers translations through a popup whose chrome tree injects
// EXTRA heading/link nodes ("Try private translations in Firefox",
// "How to fix this issue") that corrupt structure jumps mid-session.
user_pref("browser.translations.enable", false);
user_pref("browser.translations.ui.show", false);
user_pref("browser.translations.automaticallyPopup", false);
user_pref("extensions.htmlaboutaddons.recommendations.enabled", false);
