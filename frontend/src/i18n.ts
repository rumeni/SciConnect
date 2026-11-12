/**
 * The app's two languages: Serbian, which is what it opens in, and English.
 *
 * Every piece of interface text lives in the `en` table below; `sr` restates
 * the same keys, so a missing translation is a type error rather than a blank
 * on the page. Record data — institution names, instrument models, the strings
 * the API returns — is not translated: it is whatever was entered.
 *
 * Start-page texts may carry two marks, each only as a closed pair and not
 * nested:
 * `**bold**` and `__Species name__` (italic). See `Rich` in Landing.tsx.
 *
 * The choice is kept per browser and read through `useLang`, which subscribes
 * the component to changes, so switching language re-renders everything at
 * once without a reload.
 */
import { useSyncExternalStore } from "react";

export type Lang = "sr" | "en";

const STORE_KEY = "sciconnect.lang";

/** Serbian is the default; English is only used if it was asked for. */
export const DEFAULT_LANG: Lang = "sr";

export const LANGUAGES: { code: Lang; label: string; short: string }[] = [
  { code: "sr", label: "Srpski", short: "SR" },
  { code: "en", label: "English", short: "EN" },
];

const en = {
  // --- Shared ------------------------------------------------------------
  "lang.switch": "Language",
  "common.back": "Back",
  "common.cancel": "Cancel",
  "common.close": "Close",
  "common.loading": "Loading…",
  "common.saving": "Saving…",
  "common.removing": "Removing…",
  "common.remove": "Remove",
  "common.delete": "Delete",
  "common.deleting": "Deleting…",
  "common.any": "Any",
  "common.recenter": "Recenter",
  "common.requestFailed": "Request failed",
  "common.searchFailed": "Search failed",
  "common.apiUnavailable": "API is unavailable",

  // --- Brand -------------------------------------------------------------
  "brand.alt": "SciConnect",
  "brand.home": "SciConnect — home page",

  // --- Start page --------------------------------------------------------
  "landing.partners": "Partners & Sponsors",
  "landing.contact": "Contact us",
  "landing.title": "Find the lab that can run your analysis.",
  "landing.lede":
    "SciConnect brings together information about institutions, the instruments they have, the analyses they perform, the microorganisms those analyses target, and the experts they employ. Search the platform by the specific needs of your clinical or research work and quickly find the institutions that meet all of your criteria.",
  "landing.cta": "Try it",
  "landing.nav": "Page sections",
  "landing.nav.about": "About Us",
  "landing.nav.features": "Discover SciConnect",
  "landing.nav.enter": "Enter App ↗",
  "landing.problemEyebrow": "Why SciConnect matters",
  "landing.problemTitle": "The Problem We're Solving",
  "landing.problem1":
    "Information about the scientific expertise, diagnostic capabilities and laboratory resources of different institutions is often outdated, hard to access or incomplete. SciConnect brings this information together in **one searchable platform**, allowing users to easily find the right resources, experts and institutions.",
  "landing.problem2":
    "SciConnect **bridges the gap in access to information** and connects patients, healthcare professionals, researchers, scientific institutions and everyone who needs **reliable information on diagnostic services, scientific expertise and laboratory resources**. All in one place.",
  "landing.missionEyebrow": "Our purpose",
  "landing.missionTitle": "Our Mission & Vision",
  "landing.mission":
    "**Our mission** is to connect healthcare professionals, researchers, patients and institutions with the knowledge, experts and resources they need.",
  "landing.vision":
    "**Our vision** is a world where information is easy to access, opportunities for collaboration are within reach, and every new connection contributes to better healthcare and the advancement of science.",
  "landing.featuresEyebrow": "Explore possibilities",
  "landing.featuresTitle": "What Can You Do with SciConnect?",
  "landing.featuresIntro":
    "From finding a laboratory test to discovering a research partner, SciConnect helps turn scattered information into practical opportunities.",
  "landing.feature1Title": "Find diagnostic services",
  "landing.feature1Text":
    "Search for laboratory analyses, see which institutions offer them, and learn which equipment they use.",
  "landing.feature2Title": "Connect with experts",
  "landing.feature2Text":
    "Find researchers and experts in your field, get to know their expertise, and discover new opportunities for collaboration.",
  "landing.feature3Title": "Discover research resources",
  "landing.feature3Text":
    "Explore the capabilities and scientific equipment of different institutions and discover opportunities for sharing resources and building collaborations.",
  "landing.feature4Title": "Find institutions near you",
  "landing.feature4Text":
    "Find institutions that meet your needs and easily explore their locations on an interactive map.",
  "landing.tryTitle": "Try it",
  "landing.guestTitle": "Browse as a guest",
  "landing.guestText": "Explore what SciConnect has to offer – no sign-in or password needed.",
  "landing.guestButton": "Browse as guest",
  "landing.adminTitle": "Sign in as admin",
  "landing.adminText":
    "Everything a guest can do, plus adding, connecting and removing records.",
  "landing.adminButton": "Sign in as admin",

  // The catalog's model, drawn as a graph on the start page.
  "graph.node.institution": "Institution",
  "graph.node.instrument": "Instrument",
  "graph.node.analysis": "Analysis",
  "graph.node.researcher": "Researcher",
  "graph.node.microorganism": "Microorganism",
  "graph.edge.owns": "owns",
  "graph.edge.offers": "offers",
  "graph.edge.employs": "employs",
  "graph.edge.uses": "uses",
  "graph.edge.runs": "run by",
  "graph.edge.targets": "targets",
  "graph.linksInvolved": "Links involved",
  "graph.questions": "Example questions",
  "graph.q1": "Which institutions have a Real-Time PCR System?",
  "graph.q1.why": "Only instruments an institution actually owns count.",
  "graph.q2": "Who offers Whole Genome Sequencing for __Listeria monocytogenes__?",
  "graph.q2.why": "The analysis has to be stated to target that organism.",
  "graph.q3": "Who runs this analysis, and on which instrument?",
  "graph.q3.why":
    "The instrument and the researcher must belong to the same institution as the analysis.",
  "graph.q4": "All at once",
  "graph.q4.why": "Every link has to hold together, inside one institution.",

  // --- Sign in -----------------------------------------------------------
  "signIn.title": "Sign in as admin",
  "signIn.hint":
    "Admins can add institutions, instruments, analyses and researchers, connect them, and remove them. Enter the admin key you were given.",
  "signIn.keyLabel": "Admin key",
  "signIn.submit": "Sign in",
  "signIn.checking": "Checking…",
  "signIn.note":
    "The key is kept only until you close this tab. Without one you can still browse everything as a guest.",
  "signIn.expired":
    "Your admin key is no longer accepted. It may have been changed. Sign in again.",
  "signIn.unreachable": "The server could not be reached. Check your connection and try again.",
  "signIn.failed": "Signing in failed.",

  // --- Partners page ------------------------------------------------------
  "partners.home": "Back to SciConnect",
  "partners.title": "Partners & Sponsors",
  "partners.lede":
    "SciConnect is built with the help of institutions and organizations that believe research capability should be easy to find.",
  "partners.empty": "Our partners and sponsors will be listed here soon.",
  "partners.group.partners": "Partners",
  "partners.group.partners.hint":
    "Institutions that contribute data, expertise or infrastructure to SciConnect.",
  "partners.group.sponsors": "Sponsors",
  "partners.group.sponsors.hint": "Organizations and people who fund the project.",

  // --- Contact page --------------------------------------------------------
  "contact.title": "Contact",
  "contact.lede":
    "Have a question, want your institution listed in the catalogue, or would like to become a partner or sponsor? Write to us.",
  "contact.email": "Email",
  "contact.write": "Write an email",
  "footer.tagline": "© {year} SciConnect. Connecting knowledge. Creating opportunities.",
  "footer.contact": "Contact:",

  // --- Workspace ----------------------------------------------------------
  "workspace.admin": "Admin",
  "workspace.adminNote": "You can add, connect and remove records.",
  "workspace.signOut": "Sign out",
  "workspace.guest": "Guest",
  "workspace.guestNote": "You can search and open every record. Changes need an admin.",
  "workspace.signIn": "Sign in as admin",
  "workspace.startPage": "Start page",
  "workspace.views": "Views",
  "workspace.tab.search": "Search",
  "workspace.tab.nearby": "Near me",
  "workspace.tab.contribute": "Add & connect",

  // --- Search everything --------------------------------------------------
  "find.label": "Search everything by name",
  "find.placeholder": "Search institutions, instruments, analyses, organisms, researchers…",
  "find.empty": "Nothing is named like “{term}”.",
  "find.more": "More matches exist. Keep typing to narrow them.",

  // What each kind of record is called wherever one is named.
  "kind.institution": "Institution",
  "kind.researcher": "Researcher",
  "kind.instrument": "Instrument",
  "kind.analysis": "Analysis offering",
  "kind.microorganism": "Target organism",
  "kind.instrument-type": "Instrument type",
  "kind.analysis-type": "Analysis type",

  // --- Capability search --------------------------------------------------
  "search.institution": "Institution",
  "search.city": "City",
  "search.instrument": "Instrument",
  "search.analysis": "Analysis",
  "search.organism": "Target organism",
  "search.researcher": "Researcher",
  "search.submit": "Search capabilities",
  "search.clear": "Clear",
  "search.results": "Institutions found",
  "search.searching": "Searching…",
  "search.count": "{count} results",
  "search.none": "No institution satisfies the selected combination.",
  "search.hint":
    "Each filter lists only values that still match the other choices. Select any name to open its details.",
  "search.matchedInstruments": "Matching instruments",
  "search.researchers": "Researchers",
  "search.uses": "Uses",
  "search.targets": "Targets",
  "search.performedBy": "Performed by",
  "search.turnaround": "{days} day turnaround",
  "search.showMore": "Show more ({shown} of {total})",
  "search.noneAvailable": "None available",
  "search.viewDetails": "View details",
  "search.applied": "Filtered by",
  "search.removeFilter": "Remove filter: {name}",
  "search.matchesSearch": "Matches your search",
  "search.openInstitution": "Details & contact",
  "search.analyses": "Analyses",
  "search.instruments": "Instruments",
  "search.showAll": "Show all",
  "search.showLess": "Show less",
  "search.n.analysis.one": "{count} analysis",
  "search.n.analysis.few": "{count} analyses",
  "search.n.analysis.many": "{count} analyses",
  "search.n.instrument.one": "{count} instrument",
  "search.n.instrument.few": "{count} instruments",
  "search.n.instrument.many": "{count} instruments",
  "search.n.researcher.one": "{count} researcher",
  "search.n.researcher.few": "{count} researchers",
  "search.n.researcher.many": "{count} researchers",
  "search.placeholder.institution": "Enter an institution",
  "search.placeholder.city": "Enter a city",
  "search.placeholder.instrument": "Enter an instrument",
  "search.placeholder.analysis": "Enter an analysis",
  "search.placeholder.organism": "Enter a target organism",
  "search.placeholder.researcher": "Enter a researcher",
  "search.noMatches": "No matches",

  // --- Near me -------------------------------------------------------------
  "nearby.title": "Institutions near you",
  "nearby.intro":
    "Share a location and the catalogue is drawn on a map around it, nearest first. Nothing is shared until you choose to.",
  "nearby.share": "Share a location",
  "nearby.placed": "{count} placed on the map",
  "nearby.measuredFrom": "Measured from {place}.",
  "nearby.deviceNote": "This position stays in your browser.",
  "nearby.addressNote": "Only the address you typed was sent to the server.",
  "nearby.none": "No institution in the catalogue has a location yet.",
  "nearby.different": "Use a different location",
  "nearby.forget": "Forget my location",
  "nearby.mapLabel": "Map of institutions near you",
  "nearby.legendMatch": "Matches your search ({count})",
  "nearby.legendOther": "Other institutions",
  "nearby.onlyMatches": "Show only matches",
  "nearby.matchTag": "Matches search",
  "nearby.mapOf": "Map of {place}",
  "nearby.deviceLabel": "Your device location",
  "nearby.metres": "{value} m away",
  "nearby.kilometres": "{value} km away",
  "nearby.noGeolocation": "This browser cannot share a location.",
  "nearby.denied": "Location permission was declined.",
  "nearby.unknown": "Your location could not be determined.",

  // --- Location prompt -----------------------------------------------------
  "prompt.eyebrow": "Institutions near you",
  "prompt.title": "Share where you are?",
  "prompt.intro":
    "If you share a location, the institutions in the catalogue are shown on a map around it, nearest first. You can search the whole catalogue without sharing anything.",
  "prompt.useDevice": "Use my device location",
  "prompt.waiting": "Waiting for your browser…",
  "prompt.deviceNote":
    "Your browser will ask for permission. The position stays in this browser and is never sent to the server.",
  "prompt.addressLabel": "Or enter an address",
  "prompt.addressPlaceholder": "Knez Mihailova 1, Belgrade",
  "prompt.useAddress": "Use this address",
  "prompt.lookingUp": "Looking it up…",
  "prompt.addressNote":
    "The address you type is sent to the server to be looked up on OpenStreetMap.",
  "prompt.noThanks": "No thanks",
  "prompt.footer": "You can change this later from the “Near me” tab.",
  "prompt.readFailed": "Could not read your location.",
  "prompt.notFound": "That address could not be found. Try adding the city or country.",

  // --- Detail panel ---------------------------------------------------------
  "detail.title": "Details",
  "detail.couldNotLoad": "Could not load",
  "detail.couldNotRemove": "Could not remove",
  "detail.yesRemove": "Yes, remove",
  "detail.location": "Location",
  "detail.noMapAddress": "This address could not be placed on a map.",
  "detail.noAddress": "No address recorded for this institution.",
  "detail.fact.address": "Address",
  "detail.fact.location": "Location",
  "detail.fact.website": "Website",
  "detail.fact.contact": "Contact",
  "detail.fact.slug": "Slug",
  "detail.fact.title": "Title",
  "detail.fact.email": "Email",
  "detail.fact.orcid": "ORCID",
  "detail.fact.type": "Type",
  "detail.fact.manufacturer": "Manufacturer",
  "detail.fact.model": "Model",
  "detail.fact.analysisType": "Analysis type",
  "detail.fact.turnaround": "Turnaround",
  "detail.fact.turnaroundDays": "{days} days",
  "detail.fact.commonName": "Common name",
  "detail.section.instruments": "Instruments",
  "detail.section.instruments.empty": "No instruments recorded.",
  "detail.section.analyses": "Analysis offerings",
  "detail.section.analyses.empty": "No analysis offerings recorded.",
  "detail.section.researchers": "Researchers",
  "detail.section.researchers.empty": "No researchers recorded.",
  "detail.section.institution": "Institution",
  "detail.section.performs": "Performs",
  "detail.section.performs.empty": "Not linked to any analysis offering yet.",
  "detail.section.instrumentType": "Instrument type",
  "detail.section.usedBy": "Used by",
  "detail.section.usedBy.empty": "Not linked to any analysis offering yet.",
  "detail.section.analysisType": "Analysis type",
  "detail.section.usesInstruments": "Uses instruments",
  "detail.section.usesInstruments.empty": "No instrument linked yet.",
  "detail.section.targets": "Target organisms",
  "detail.section.targets.empty": "No target organism linked yet.",
  "detail.section.performedBy": "Performed by",
  "detail.section.performedBy.empty": "No researcher linked yet.",
  "detail.section.detectedBy": "Detected by",
  "detail.section.detectedBy.empty": "No analysis offering targets this organism yet.",
  "detail.section.owners": "Institutions owning one",
  "detail.section.owners.empty": "No institution owns this instrument type yet.",
  "detail.section.units": "Individual units",
  "detail.section.units.empty": "No units recorded.",
  "detail.section.offerers": "Institutions offering it",
  "detail.section.offerers.empty": "No institution offers this analysis type yet.",
  "detail.section.offerings": "Offerings",
  "detail.section.offerings.empty": "No offerings recorded.",
  "detail.remove.deletes":
    "Removes this {what} from {owner}. The record is deleted, because it belongs to exactly one institution and cannot stand without it.",
  "detail.remove.what.instrument": "instrument",
  "detail.remove.what.offering": "offering",
  "detail.remove.what.researcher": "researcher",
  "detail.remove.itsInstitution": "its institution",
  "detail.remove.instrument": "The offering stops using this instrument. Both records stay.",
  "detail.remove.target": "The offering stops detecting this organism. Both records stay.",
  "detail.remove.researcher": "They stop performing this offering. Both records stay.",

  // --- Add & connect ---------------------------------------------------------
  "manage.catalog": "Catalog entries",
  "manage.catalog.hint":
    "Shared vocabulary and organizations. Everything else is attached to these.",
  "manage.capabilities": "Institution capabilities",
  "manage.capabilities.hint":
    "Concrete instrument units and analysis offerings belonging to one institution.",
  "manage.connections": "Connections",
  "manage.connections.hint":
    "An analysis is only searchable through an instrument, organism or researcher once the relationship is stated here. Only records from the same institution can be connected.",
  "manage.removing": "Removing",
  "manage.removing.hint":
    "Disconnecting ends a relationship and keeps both records. Deleting removes a record, and is refused while anything still depends on it.",

  "manage.institution.title": "Institution",
  "manage.institution.hint":
    "The slug comes from the name when left empty. The address is looked up to place the institution on a map.",
  "manage.institution.submit": "Create institution",
  "manage.institution.created": "Created {name}",
  "manage.institution.createdNoMap": "Created {name}, but the address could not be placed on a map",

  "manage.instrumentType.title": "Instrument type",
  "manage.instrumentType.hint": "A normalized concept such as Real-Time PCR System.",
  "manage.instrumentType.submit": "Create instrument type",
  "manage.analysisType.title": "Analysis type",
  "manage.analysisType.hint": "A normalized concept such as Whole Genome Sequencing.",
  "manage.analysisType.submit": "Create analysis type",
  "manage.created": "Created {name}",

  "manage.organism.title": "Target organism",
  "manage.organism.hint":
    "A microorganism an analysis can detect, identify or otherwise process.",
  "manage.organism.submit": "Create organism",

  "manage.researcher.title": "Researcher",
  "manage.researcher.hint": "A researcher belongs to exactly one institution.",
  "manage.researcher.submit": "Create researcher",

  "manage.instrument.title": "Institution instrument",
  "manage.instrument.hint": "A concrete instrument unit owned by one institution.",
  "manage.instrument.submit": "Create instrument",
  "manage.instrument.created": "Instrument added to the institution",

  "manage.analysis.title": "Institution analysis",
  "manage.analysis.hint":
    "A concrete service offered by one institution. One offering per analysis type.",
  "manage.analysis.submit": "Create analysis offering",
  "manage.analysis.created": "Analysis offering created",

  "manage.field.name": "Name",
  "manage.field.description": "Description",
  "manage.field.address": "Street address",
  "manage.field.addressPlaceholder": "Bulevar oslobodjenja 18",
  "manage.field.city": "City",
  "manage.field.country": "Country",
  "manage.field.website": "Website",
  "manage.field.contactEmail": "Contact email",
  "manage.field.scientificName": "Scientific name",
  "manage.field.commonName": "Common name",
  "manage.field.institution": "Institution",
  "manage.field.fullName": "Full name",
  "manage.field.title": "Title",
  "manage.field.titlePlaceholder": "Research Associate",
  "manage.field.email": "Email",
  "manage.field.orcid": "ORCID",
  "manage.field.expertise": "Expertise",
  "manage.field.instrumentType": "Instrument type",
  "manage.field.analysisType": "Analysis type",
  "manage.field.displayName": "Display name",
  "manage.field.manufacturer": "Manufacturer",
  "manage.field.model": "Model",
  "manage.field.status": "Status",
  "manage.field.publicName": "Public name",
  "manage.field.turnaround": "Turnaround days",
  "manage.field.optional": "optional",
  "manage.field.availability": "Availability",
  "manage.field.usage": "Usage",
  "manage.field.role": "Role",
  "manage.field.kind": "Kind",
  "manage.field.record": "Record",

  "manage.pick.institution": "Select an institution",
  "manage.pick.type": "Select a type",
  "manage.pick.kind": "Select a kind",
  "manage.pick.record": "Select a record",
  "manage.pick.kindFirst": "Choose a kind first",
  "manage.pick.offering": "Select an analysis offering",
  "manage.pick.instrument": "Select an instrument",
  "manage.pick.organism": "Select a target organism",
  "manage.pick.researcher": "Select a researcher",

  "status.operational": "operational",
  "status.maintenance": "maintenance",
  "status.unavailable": "unavailable",
  "status.archived": "archived",
  "status.available": "available",
  "status.limited": "limited",
  "role.required": "required",
  "role.optional": "optional",
  "role.alternative": "alternative",
  "role.lead": "lead",
  "role.contributor": "contributor",
  "role.contact": "contact",

  "connect.picker": "Analysis offering to connect",
  "connect.pickFirst": "Select an analysis offering to connect it to other records.",
  "connect.instrument.title": "Use an instrument",
  "connect.instrument.hint": "Only instruments owned by the same institution can be used.",
  "connect.instrument.submit": "Link instrument",
  "connect.instrument.empty": "This institution has no instruments yet.",
  "connect.instrument.done": "Instrument linked",
  "connect.organism.title": "Detect a target organism",
  "connect.organism.hint": "States that this offering can process the organism.",
  "connect.organism.submit": "Link organism",
  "connect.organism.empty": "No organisms in the catalog yet.",
  "connect.organism.done": "Target organism linked",
  "connect.researcher.title": "Assign a researcher",
  "connect.researcher.hint": "Only researchers of the same institution can be assigned.",
  "connect.researcher.submit": "Link researcher",
  "connect.researcher.empty": "This institution has no researchers yet.",
  "connect.researcher.done": "Researcher linked",
  "connect.unnamedInstrument": "Instrument {id}",
  "connect.unnamedAnalysis": "Analysis {id}",
  "connect.unnamedOffering": "Offering {id}",
  "connect.unnamedInstitution": "Institution {id}",

  "current.title": "Current connections",
  "current.hint":
    "Disconnecting removes only the relationship. Both records stay in the catalogue.",
  "current.readFailed": "Could not read this offering's connections.",
  "current.empty": "This offering is not connected to anything yet.",
  "current.usesInstrument": "Uses this instrument",
  "current.detectsOrganism": "Detects this organism",
  "current.performedByAs": "Performed by, as {role}",
  "current.performedBy": "Performed by",
  "current.disconnect": "Disconnect",
  "current.disconnectFailed": "Could not disconnect",

  "delete.title": "Delete a record",
  "delete.hint":
    "A catalogue entry still in use cannot be deleted; disconnect or delete what depends on it first. Deleting a researcher is how someone who has left the institution is removed, because their affiliation is part of the record rather than a connection.",
  "delete.confirm": "Yes, delete {label}",
  "delete.confirmIt": "it",
  "delete.cascade": "Delete {label} and everything it holds",
  "delete.failed": "Could not delete",

  // --- What the client itself says about a failed request ------------------
  "api.keyWrong": "That admin key is not right.",
  "api.keyExpired": "Your admin key is no longer accepted. Sign in again.",
  "api.keyNeeded": "Changing the catalog needs an admin key. Sign in as admin.",
  "api.tooMany": "Too many requests in a short time.",
  // Abbreviated on purpose: "second" declines in Serbian by the number in
  // front of it, and the symbol sidesteps that without reading oddly.
  "api.retry": "Try again in {seconds} s.",
  "api.requestFailed": "Request failed ({status})",
} as const;

export type MessageKey = keyof typeof en;

const sr: Record<MessageKey, string> = {
  // --- Shared ------------------------------------------------------------
  "lang.switch": "Jezik",
  "common.back": "Nazad",
  "common.cancel": "Otkaži",
  "common.close": "Zatvori",
  "common.loading": "Učitavanje…",
  "common.saving": "Čuvanje…",
  "common.removing": "Uklanjanje…",
  "common.remove": "Ukloni",
  "common.delete": "Obriši",
  "common.deleting": "Brisanje…",
  "common.any": "Bilo koji",
  "common.recenter": "Centriraj",
  "common.requestFailed": "Zahtev nije uspeo",
  "common.searchFailed": "Pretraga nije uspela",
  "common.apiUnavailable": "Server nije dostupan",

  // --- Brand -------------------------------------------------------------
  "brand.alt": "SciConnect",
  "brand.home": "SciConnect — početna strana",

  // --- Start page --------------------------------------------------------
  "landing.partners": "Partneri i sponzori",
  "landing.contact": "Kontaktirajte nas",
  "landing.title": "Pronađite laboratoriju koja može da uradi Vašu analizu.",
  "landing.lede":
    "SciConnect povezuje informacije o ustanovama, instrumentima kojima raspolažu, analizama koje obavljaju, mikroorganizmima na koje su te analize usmerene i stručnjacima zaposlenim u tim ustanovama. Pretražite platformu prema konkretnim potrebama svog kliničkog ili istraživačkog rada i brzo pronađite ustanove koje ispunjavaju sve Vaše kriterijume.",
  "landing.cta": "Isprobajte",
  "landing.nav": "Delovi stranice",
  "landing.nav.about": "O nama",
  "landing.nav.features": "Otkrijte SciConnect",
  "landing.nav.enter": "Uđite u aplikaciju ↗",
  "landing.problemEyebrow": "Zašto je SciConnect važan",
  "landing.problemTitle": "Problem koji rešavamo",
  "landing.problem1":
    "Informacije o naučnoj ekspertizi, dijagnostičkim mogućnostima i laboratorijskim resursima različitih ustanova su često zastarele, teško dostupne ili nepotpune. SciConnect objedinjuje ove informacije na **jedinstvenoj platformi za pretragu**, omogućavajući korisnicima da jednostavno pronađu odgovarajuće resurse, stručnjake i ustanove.",
  "landing.problem2":
    "SciConnect **premošćuje jaz u dostupnosti informacija** i povezuje pacijente, zdravstvene radnike, istraživače, naučne ustanove i sve kojima su potrebne **pouzdane informacije o dijagnostičkim uslugama, naučnoj ekspertizi i laboratorijskim resursima**. Na jednom mestu.",
  "landing.missionEyebrow": "Naša svrha",
  "landing.missionTitle": "Naša misija i vizija",
  "landing.mission":
    "**Naša misija** je da povežemo zdravstvene radnike, istraživače, pacijente i ustanove sa znanjem, stručnjacima i resursima koji su im potrebni.",
  "landing.vision":
    "**Naša vizija** je svet u kojem su informacije lako dostupne, prilike za saradnju nadohvat ruke, a svako novo povezivanje doprinosi kvalitetnijoj zdravstvenoj zaštiti i napretku nauke.",
  "landing.featuresEyebrow": "Istražite mogućnosti",
  "landing.featuresTitle": "Šta možete da uradite uz SciConnect?",
  "landing.featuresIntro":
    "Od pronalaženja laboratorijske analize do otkrivanja partnera za istraživanje, SciConnect pretvara rasute informacije u praktične prilike.",
  "landing.feature1Title": "Pronađite dijagnostičke usluge",
  "landing.feature1Text":
    "Pretražite laboratorijske analize, pogledajte koje ih ustanove nude i saznajte koju opremu koriste.",
  "landing.feature2Title": "Povežite se sa stručnjacima",
  "landing.feature2Text":
    "Pronađite istraživače i stručnjake iz svoje oblasti, upoznajte se sa njihovom ekspertizom i otkrijte nove mogućnosti za saradnju.",
  "landing.feature3Title": "Otkrijte istraživačke resurse",
  "landing.feature3Text":
    "Istražite mogućnosti i naučnu opremu različitih ustanova i otkrijte prilike za zajedničko korišćenje resursa i uspostavljanje saradnje.",
  "landing.feature4Title": "Pronađite ustanove blizu Vas",
  "landing.feature4Text":
    "Pronađite ustanove koje odgovaraju Vašim potrebama i jednostavno istražite njihove lokacije na interaktivnoj mapi.",
  "landing.tryTitle": "Isprobajte",
  "landing.guestTitle": "Pregledajte kao gost",
  "landing.guestText":
    "Ispitajte mogućnosti koje Vam nudi SciConnect – bez prijave i lozinke.",
  "landing.guestButton": "Uđite kao gost",
  "landing.adminTitle": "Prijavite se kao administrator",
  "landing.adminText":
    "Sve što gost može, uz dodavanje, povezivanje i uklanjanje zapisa.",
  "landing.adminButton": "Prijava za administratore",

  "graph.node.institution": "Ustanova",
  "graph.node.instrument": "Instrument",
  "graph.node.analysis": "Analiza",
  "graph.node.researcher": "Istraživač",
  "graph.node.microorganism": "Mikroorganizam",
  "graph.edge.owns": "poseduje",
  "graph.edge.offers": "nudi",
  "graph.edge.employs": "zapošljava",
  "graph.edge.uses": "koristi",
  "graph.edge.runs": "izvodi",
  "graph.edge.targets": "cilja",
  "graph.linksInvolved": "Veze koje učestvuju",
  "graph.questions": "Primeri pitanja",
  "graph.q1": "Koje ustanove imaju Real-Time PCR sistem?",
  "graph.q1.why": "Računaju se samo instrumenti koje ustanova zaista poseduje.",
  "graph.q2": "Ko nudi uslugu sekvenciranja celog genoma za __Listeria monocytogenes__?",
  "graph.q2.why": "Za analizu mora biti navedeno da cilja taj organizam.",
  "graph.q3": "Ko izvodi ovu analizu i na kom instrumentu?",
  "graph.q3.why":
    "Instrument i istraživač moraju pripadati istoj ustanovi kao i analiza.",
  "graph.q4": "Sve odjednom",
  "graph.q4.why": "Svaka veza mora da se poklopi, unutar jedne ustanove.",

  // --- Sign in -----------------------------------------------------------
  "signIn.title": "Prijava za administratore",
  "signIn.hint":
    "Administratori mogu da dodaju ustanove, instrumente, analize i istraživače, da ih povezuju i uklanjaju. Unesite administratorski ključ koji ste dobili.",
  "signIn.keyLabel": "Administratorski ključ",
  "signIn.submit": "Prijavite se",
  "signIn.checking": "Provera…",
  "signIn.note":
    "Ključ se čuva samo dok ne zatvorite ovu karticu. I bez njega možete sve da pregledate kao gost.",
  "signIn.expired":
    "Vaš administratorski ključ više nije prihvaćen. Možda je promenjen. Prijavite se ponovo.",
  "signIn.unreachable": "Server nije dostupan. Proverite vezu i pokušajte ponovo.",
  "signIn.failed": "Prijava nije uspela.",

  // --- Partners page ------------------------------------------------------
  "partners.home": "Nazad na SciConnect",
  "partners.title": "Partneri i sponzori",
  "partners.lede":
    "SciConnect nastaje uz pomoć ustanova i organizacija koje veruju da istraživačke mogućnosti treba da budu lako dostupne.",
  "partners.empty": "Naši partneri i sponzori biće uskoro navedeni ovde.",
  "partners.group.partners": "Partneri",
  "partners.group.partners.hint":
    "Ustanove koje SciConnectu doprinose podacima, znanjem ili infrastrukturom.",
  "partners.group.sponsors": "Sponzori",
  "partners.group.sponsors.hint": "Organizacije i pojedinci koji finansijski podržavaju projekat.",

  // --- Contact page --------------------------------------------------------
  "contact.title": "Kontakt",
  "contact.lede":
    "Imate pitanje, želite da Vaša ustanova bude u katalogu ili da postanete partner ili sponzor? Pišite nam.",
  "contact.email": "E-pošta",
  "contact.write": "Pošaljite mejl",
  "footer.tagline": "© {year} SciConnect. Povezujemo znanje. Stvaramo prilike.",
  "footer.contact": "Kontakt:",

  // --- Workspace ----------------------------------------------------------
  "workspace.admin": "Administrator",
  "workspace.adminNote": "Možete da dodajete, povezujete i uklanjate zapise.",
  "workspace.signOut": "Odjava",
  "workspace.guest": "Gost",
  "workspace.guestNote":
    "Možete da pretražujete i otvarate sve zapise. Za izmene je potreban administrator.",
  "workspace.signIn": "Prijava za administratore",
  "workspace.startPage": "Početna strana",
  "workspace.views": "Prikazi",
  "workspace.tab.search": "Pretraga",
  "workspace.tab.nearby": "U mojoj blizini",
  "workspace.tab.contribute": "Dodaj i poveži",

  // --- Search everything --------------------------------------------------
  "find.label": "Pretraga svega po nazivu",
  "find.placeholder": "Pretražite ustanove, instrumente, analize, organizme, istraživače…",
  "find.empty": "Ništa se ne zove „{term}“.",
  "find.more": "Ima još rezultata. Nastavite da kucate da biste ih suzili.",

  "kind.institution": "Ustanova",
  "kind.researcher": "Istraživač",
  "kind.instrument": "Instrument",
  "kind.analysis": "Ponuđena analiza",
  "kind.microorganism": "Ciljni organizam",
  "kind.instrument-type": "Tip instrumenta",
  "kind.analysis-type": "Tip analize",

  // --- Capability search --------------------------------------------------
  "search.institution": "Ustanova",
  "search.city": "Grad",
  "search.instrument": "Instrument",
  "search.analysis": "Analiza",
  "search.organism": "Ciljni organizam",
  "search.researcher": "Istraživač",
  "search.submit": "Pretraži mogućnosti",
  "search.clear": "Poništi",
  "search.results": "Pronađene ustanove",
  "search.searching": "Pretraga…",
  "search.count": "Rezultata: {count}",
  "search.none": "Nijedna ustanova ne ispunjava izabranu kombinaciju.",
  "search.hint":
    "Svaki filter nudi samo vrednosti koje se i dalje slažu sa ostalim izborima. Kliknite na bilo koji naziv da biste otvorili detalje.",
  "search.matchedInstruments": "Instrumenti koji odgovaraju",
  "search.researchers": "Istraživači",
  "search.uses": "Koristi",
  "search.targets": "Cilja",
  "search.performedBy": "Izvodi",
  "search.turnaround": "Rok izrade: {days} dana",
  "search.showMore": "Prikaži još ({shown} od {total})",
  "search.noneAvailable": "Nema dostupnih",
  "search.viewDetails": "Prikaži detalje",
  "search.applied": "Filtrirano po",
  "search.removeFilter": "Ukloni filter: {name}",
  "search.matchesSearch": "Odgovara pretrazi",
  "search.openInstitution": "Detalji i kontakt",
  "search.analyses": "Analize",
  "search.instruments": "Instrumenti",
  "search.showAll": "Prikaži sve",
  "search.showLess": "Prikaži manje",
  "search.n.analysis.one": "{count} analiza",
  "search.n.analysis.few": "{count} analize",
  "search.n.analysis.many": "{count} analiza",
  "search.n.instrument.one": "{count} instrument",
  "search.n.instrument.few": "{count} instrumenta",
  "search.n.instrument.many": "{count} instrumenata",
  "search.n.researcher.one": "{count} istraživač",
  "search.n.researcher.few": "{count} istraživača",
  "search.n.researcher.many": "{count} istraživača",
  "search.placeholder.institution": "Unesite ustanovu",
  "search.placeholder.city": "Unesite grad",
  "search.placeholder.instrument": "Unesite instrument",
  "search.placeholder.analysis": "Unesite analizu",
  "search.placeholder.organism": "Unesite ciljni organizam",
  "search.placeholder.researcher": "Unesite istraživača",
  "search.noMatches": "Nema rezultata",

  // --- Near me -------------------------------------------------------------
  "nearby.title": "Ustanove u Vašoj blizini",
  "nearby.intro":
    "Podelite lokaciju i katalog će biti prikazan na mapi oko nje, najbliže prvo. Ništa se ne deli dok to sami ne izaberete.",
  "nearby.share": "Podelite lokaciju",
  "nearby.placed": "Na mapi: {count}",
  "nearby.measuredFrom": "Mereno od: {place}.",
  "nearby.deviceNote": "Ova pozicija ostaje u Vašem pregledaču.",
  "nearby.addressNote": "Serveru je poslata samo adresa koju ste uneli.",
  "nearby.none": "Nijedna ustanova u katalogu još nema lokaciju.",
  "nearby.different": "Koristi drugu lokaciju",
  "nearby.forget": "Zaboravi moju lokaciju",
  "nearby.mapLabel": "Mapa ustanova u Vašoj blizini",
  "nearby.legendMatch": "Odgovara pretrazi ({count})",
  "nearby.legendOther": "Ostale ustanove",
  "nearby.onlyMatches": "Prikaži samo pronađene",
  "nearby.matchTag": "Odgovara pretrazi",
  "nearby.mapOf": "Mapa: {place}",
  "nearby.deviceLabel": "Lokacija Vašeg uređaja",
  "nearby.metres": "{value} m daleko",
  "nearby.kilometres": "{value} km daleko",
  "nearby.noGeolocation": "Ovaj pregledač ne može da podeli lokaciju.",
  "nearby.denied": "Dozvola za lokaciju je odbijena.",
  "nearby.unknown": "Vaša lokacija nije mogla da se odredi.",

  // --- Location prompt -----------------------------------------------------
  "prompt.eyebrow": "Ustanove u Vašoj blizini",
  "prompt.title": "Želite li da podelite gde se nalazite?",
  "prompt.intro":
    "Ako podelite lokaciju, ustanove iz kataloga biće prikazane na mapi oko nje, najbliže prvo. Ceo katalog možete pretraživati i bez deljenja bilo čega.",
  "prompt.useDevice": "Koristi lokaciju mog uređaja",
  "prompt.waiting": "Čeka se Vaš pregledač…",
  "prompt.deviceNote":
    "Pregledač će zatražiti dozvolu. Pozicija ostaje u ovom pregledaču i nikada se ne šalje serveru.",
  "prompt.addressLabel": "Ili unesite adresu",
  "prompt.addressPlaceholder": "Knez Mihailova 1, Beograd",
  "prompt.useAddress": "Koristi ovu adresu",
  "prompt.lookingUp": "Traženje…",
  "prompt.addressNote":
    "Adresa koju unesete šalje se serveru da bi bila pronađena na OpenStreetMap-u.",
  "prompt.noThanks": "Ne, hvala",
  "prompt.footer": "Ovo možete promeniti kasnije na kartici „U mojoj blizini“.",
  "prompt.readFailed": "Vaša lokacija nije mogla da se pročita.",
  "prompt.notFound": "Ta adresa nije pronađena. Pokušajte da dodate grad ili državu.",

  // --- Detail panel ---------------------------------------------------------
  "detail.title": "Detalji",
  "detail.couldNotLoad": "Učitavanje nije uspelo",
  "detail.couldNotRemove": "Uklanjanje nije uspelo",
  "detail.yesRemove": "Da, ukloni",
  "detail.location": "Lokacija",
  "detail.noMapAddress": "Ova adresa nije mogla da se postavi na mapu.",
  "detail.noAddress": "Za ovu ustanovu nije zabeležena adresa.",
  "detail.fact.address": "Adresa",
  "detail.fact.location": "Lokacija",
  "detail.fact.website": "Veb sajt",
  "detail.fact.contact": "Kontakt",
  "detail.fact.slug": "Identifikator",
  "detail.fact.title": "Zvanje",
  "detail.fact.email": "E-pošta",
  "detail.fact.orcid": "ORCID",
  "detail.fact.type": "Tip",
  "detail.fact.manufacturer": "Proizvođač",
  "detail.fact.model": "Model",
  "detail.fact.analysisType": "Tip analize",
  "detail.fact.turnaround": "Rok izrade",
  "detail.fact.turnaroundDays": "{days} dana",
  "detail.fact.commonName": "Uobičajeni naziv",
  "detail.section.instruments": "Instrumenti",
  "detail.section.instruments.empty": "Nema zabeleženih instrumenata.",
  "detail.section.analyses": "Ponuđene analize",
  "detail.section.analyses.empty": "Nema zabeleženih ponuđenih analiza.",
  "detail.section.researchers": "Istraživači",
  "detail.section.researchers.empty": "Nema zabeleženih istraživača.",
  "detail.section.institution": "Ustanova",
  "detail.section.performs": "Izvodi",
  "detail.section.performs.empty": "Još nije povezan ni sa jednom ponuđenom analizom.",
  "detail.section.instrumentType": "Tip instrumenta",
  "detail.section.usedBy": "Koriste ga",
  "detail.section.usedBy.empty": "Još nije povezan ni sa jednom ponuđenom analizom.",
  "detail.section.analysisType": "Tip analize",
  "detail.section.usesInstruments": "Koristi instrumente",
  "detail.section.usesInstruments.empty": "Još nije povezan nijedan instrument.",
  "detail.section.targets": "Ciljni organizmi",
  "detail.section.targets.empty": "Još nije povezan nijedan ciljni organizam.",
  "detail.section.performedBy": "Izvodi",
  "detail.section.performedBy.empty": "Još nije povezan nijedan istraživač.",
  "detail.section.detectedBy": "Detektuju ga",
  "detail.section.detectedBy.empty": "Nijedna ponuđena analiza još ne cilja ovaj organizam.",
  "detail.section.owners": "Ustanove koje ga poseduju",
  "detail.section.owners.empty": "Nijedna ustanova još ne poseduje ovaj tip instrumenta.",
  "detail.section.units": "Pojedinačni primerci",
  "detail.section.units.empty": "Nema zabeleženih primeraka.",
  "detail.section.offerers": "Ustanove koje je nude",
  "detail.section.offerers.empty": "Nijedna ustanova još ne nudi ovaj tip analize.",
  "detail.section.offerings": "Ponude",
  "detail.section.offerings.empty": "Nema zabeleženih ponuda.",
  "detail.remove.deletes":
    "Uklanja {what} iz ustanove {owner}. Zapis se briše, jer pripada tačno jednoj ustanovi i ne može postojati bez nje.",
  "detail.remove.what.instrument": "ovaj instrument",
  "detail.remove.what.offering": "ovu ponudu",
  "detail.remove.what.researcher": "ovog istraživača",
  "detail.remove.itsInstitution": "njegove ustanove",
  "detail.remove.instrument": "Ponuda prestaje da koristi ovaj instrument. Oba zapisa ostaju.",
  "detail.remove.target": "Ponuda prestaje da detektuje ovaj organizam. Oba zapisa ostaju.",
  "detail.remove.researcher": "Prestaje da izvodi ovu ponudu. Oba zapisa ostaju.",

  // --- Add & connect ---------------------------------------------------------
  "manage.catalog": "Stavke kataloga",
  "manage.catalog.hint":
    "Zajednički pojmovnik i organizacije. Sve ostalo se vezuje za njih.",
  "manage.capabilities": "Mogućnosti ustanove",
  "manage.capabilities.hint":
    "Konkretni primerci instrumenata i ponuđene analize koji pripadaju jednoj ustanovi.",
  "manage.connections": "Veze",
  "manage.connections.hint":
    "Analiza je pretraživa preko instrumenta, organizma ili istraživača tek kada se ovde navede ta veza. Povezati se mogu samo zapisi iz iste ustanove.",
  "manage.removing": "Uklanjanje",
  "manage.removing.hint":
    "Raskidanje veze prekida odnos, a oba zapisa ostaju. Brisanje uklanja zapis i odbija se dok god nešto zavisi od njega.",

  "manage.institution.title": "Ustanova",
  "manage.institution.hint":
    "Identifikator se izvodi iz naziva ako se ostavi prazan. Adresa se pretražuje da bi ustanova bila postavljena na mapu.",
  "manage.institution.submit": "Kreiraj ustanovu",
  "manage.institution.created": "Kreirano: {name}",
  "manage.institution.createdNoMap":
    "Kreirano: {name}, ali adresa nije mogla da se postavi na mapu",

  "manage.instrumentType.title": "Tip instrumenta",
  "manage.instrumentType.hint": "Normalizovan pojam, na primer Real-Time PCR sistem.",
  "manage.instrumentType.submit": "Kreiraj tip instrumenta",
  "manage.analysisType.title": "Tip analize",
  "manage.analysisType.hint": "Normalizovan pojam, na primer sekvenciranje celog genoma.",
  "manage.analysisType.submit": "Kreiraj tip analize",
  "manage.created": "Kreirano: {name}",

  "manage.organism.title": "Ciljni organizam",
  "manage.organism.hint":
    "Mikroorganizam koji analiza može da detektuje, identifikuje ili na drugi način obradi.",
  "manage.organism.submit": "Kreiraj organizam",

  "manage.researcher.title": "Istraživač",
  "manage.researcher.hint": "Istraživač pripada tačno jednoj ustanovi.",
  "manage.researcher.submit": "Kreiraj istraživača",

  "manage.instrument.title": "Instrument ustanove",
  "manage.instrument.hint": "Konkretan primerak instrumenta u vlasništvu jedne ustanove.",
  "manage.instrument.submit": "Kreiraj instrument",
  "manage.instrument.created": "Instrument je dodat ustanovi",

  "manage.analysis.title": "Analiza ustanove",
  "manage.analysis.hint":
    "Konkretna usluga koju nudi jedna ustanova. Jedna ponuda po tipu analize.",
  "manage.analysis.submit": "Kreiraj ponuđenu analizu",
  "manage.analysis.created": "Ponuđena analiza je kreirana",

  "manage.field.name": "Naziv",
  "manage.field.description": "Opis",
  "manage.field.address": "Ulica i broj",
  "manage.field.addressPlaceholder": "Bulevar oslobođenja 18",
  "manage.field.city": "Grad",
  "manage.field.country": "Država",
  "manage.field.website": "Veb sajt",
  "manage.field.contactEmail": "Kontakt e-pošta",
  "manage.field.scientificName": "Naučni naziv",
  "manage.field.commonName": "Uobičajeni naziv",
  "manage.field.institution": "Ustanova",
  "manage.field.fullName": "Ime i prezime",
  "manage.field.title": "Zvanje",
  "manage.field.titlePlaceholder": "Istraživač saradnik",
  "manage.field.email": "E-pošta",
  "manage.field.orcid": "ORCID",
  "manage.field.expertise": "Oblast ekspertize",
  "manage.field.instrumentType": "Tip instrumenta",
  "manage.field.analysisType": "Tip analize",
  "manage.field.displayName": "Prikazni naziv",
  "manage.field.manufacturer": "Proizvođač",
  "manage.field.model": "Model",
  "manage.field.status": "Status",
  "manage.field.publicName": "Javni naziv",
  "manage.field.turnaround": "Rok izrade (dana)",
  "manage.field.optional": "neobavezno",
  "manage.field.availability": "Dostupnost",
  "manage.field.usage": "Način korišćenja",
  "manage.field.role": "Uloga",
  "manage.field.kind": "Vrsta",
  "manage.field.record": "Zapis",

  "manage.pick.institution": "Izaberite ustanovu",
  "manage.pick.type": "Izaberite tip",
  "manage.pick.kind": "Izaberite vrstu",
  "manage.pick.record": "Izaberite zapis",
  "manage.pick.kindFirst": "Prvo izaberite vrstu",
  "manage.pick.offering": "Izaberite ponuđenu analizu",
  "manage.pick.instrument": "Izaberite instrument",
  "manage.pick.organism": "Izaberite ciljni organizam",
  "manage.pick.researcher": "Izaberite istraživača",

  "status.operational": "u funkciji",
  "status.maintenance": "na održavanju",
  "status.unavailable": "nedostupno",
  "status.archived": "arhivirano",
  "status.available": "dostupno",
  "status.limited": "ograničeno",
  "role.required": "obavezan",
  "role.optional": "neobavezan",
  "role.alternative": "alternativa",
  "role.lead": "nosilac",
  "role.contributor": "saradnik",
  "role.contact": "kontakt",

  "connect.picker": "Ponuđena analiza koja se povezuje",
  "connect.pickFirst": "Izaberite ponuđenu analizu da biste je povezali sa drugim zapisima.",
  "connect.instrument.title": "Koristi instrument",
  "connect.instrument.hint": "Mogu se koristiti samo instrumenti iste ustanove.",
  "connect.instrument.submit": "Poveži instrument",
  "connect.instrument.empty": "Ova ustanova još nema instrumente.",
  "connect.instrument.done": "Instrument je povezan",
  "connect.organism.title": "Detektuje ciljni organizam",
  "connect.organism.hint": "Navodi da ova ponuda može da obradi taj organizam.",
  "connect.organism.submit": "Poveži organizam",
  "connect.organism.empty": "U katalogu još nema organizama.",
  "connect.organism.done": "Ciljni organizam je povezan",
  "connect.researcher.title": "Dodeli istraživača",
  "connect.researcher.hint": "Mogu se dodeliti samo istraživači iste ustanove.",
  "connect.researcher.submit": "Poveži istraživača",
  "connect.researcher.empty": "Ova ustanova još nema istraživače.",
  "connect.researcher.done": "Istraživač je povezan",
  "connect.unnamedInstrument": "Instrument {id}",
  "connect.unnamedAnalysis": "Analiza {id}",
  "connect.unnamedOffering": "Ponuda {id}",
  "connect.unnamedInstitution": "Ustanova {id}",

  "current.title": "Postojeće veze",
  "current.hint": "Raskidanje veze uklanja samo odnos. Oba zapisa ostaju u katalogu.",
  "current.readFailed": "Veze ove ponude nisu mogle da se pročitaju.",
  "current.empty": "Ova ponuda još nije povezana ni sa čim.",
  "current.usesInstrument": "Koristi ovaj instrument",
  "current.detectsOrganism": "Detektuje ovaj organizam",
  "current.performedByAs": "Izvodi, kao {role}",
  "current.performedBy": "Izvodi",
  "current.disconnect": "Raskini vezu",
  "current.disconnectFailed": "Veza nije mogla da se raskine",

  "delete.title": "Obriši zapis",
  "delete.hint":
    "Stavka kataloga koja je još u upotrebi ne može da se obriše; prvo raskinite veze ili obrišite ono što od nje zavisi. Brisanje istraživača je način da se ukloni neko ko je napustio ustanovu, jer je pripadnost deo zapisa, a ne veza.",
  "delete.confirm": "Da, obriši: {label}",
  "delete.confirmIt": "ovo",
  "delete.cascade": "Obriši {label} i sve što sadrži",
  "delete.failed": "Brisanje nije uspelo",

  "api.keyWrong": "Taj administratorski ključ nije ispravan.",
  "api.keyExpired": "Vaš administratorski ključ više nije prihvaćen. Prijavite se ponovo.",
  "api.keyNeeded":
    "Za izmenu kataloga potreban je administratorski ključ. Prijavite se kao administrator.",
  "api.tooMany": "Previše zahteva u kratkom vremenu.",
  "api.retry": "Pokušajte ponovo za {seconds} s.",
  "api.requestFailed": "Zahtev nije uspeo ({status})",
};

const TABLES: Record<Lang, Record<MessageKey, string>> = { en, sr };

/** The language a tab last chose, or Serbian the first time around. */
function read(): Lang {
  try {
    const stored = localStorage.getItem(STORE_KEY);
    if (stored === "sr" || stored === "en") return stored;
  } catch {
    /* A browser that refuses storage simply opens in the default language. */
  }
  return DEFAULT_LANG;
}

let current: Lang = read();
const listeners = new Set<() => void>();

// Set before React mounts so screen readers and spell-checkers see the right
// language on the very first paint.
if (typeof document !== "undefined") document.documentElement.lang = current;

export function getLang(): Lang {
  return current;
}

export function setLang(next: Lang): void {
  if (next === current) return;
  current = next;
  try {
    localStorage.setItem(STORE_KEY, next);
  } catch {
    /* the choice just will not survive a reload */
  }
  if (typeof document !== "undefined") document.documentElement.lang = next;
  listeners.forEach((notify) => notify());
}

function subscribe(notify: () => void): () => void {
  listeners.add(notify);
  return () => listeners.delete(notify);
}

/** Fill `{name}` placeholders from `values`. */
function format(template: string, values?: Record<string, string | number>): string {
  if (!values) return template;
  return template.replace(/\{(\w+)\}/g, (whole, name: string) =>
    name in values ? String(values[name]) : whole,
  );
}

export type Translate = (key: MessageKey, values?: Record<string, string | number>) => string;

/** Translate against a known language, outside of React. */
export function translate(
  lang: Lang,
  key: MessageKey,
  values?: Record<string, string | number>,
): string {
  return format(TABLES[lang][key] ?? TABLES.en[key] ?? key, values);
}

/** The chosen language, re-rendering the component whenever it changes. */
export function useLang(): Lang {
  return useSyncExternalStore(subscribe, getLang, () => DEFAULT_LANG);
}

/**
 * One translator per language, made once.
 *
 * `useT` has to hand back the same function for as long as the language does
 * not change: a fresh closure on every render would make any effect that lists
 * the translator among its dependencies re-run forever.
 */
const TRANSLATORS: Record<Lang, Translate> = {
  en: (key, values) => translate("en", key, values),
  sr: (key, values) => translate("sr", key, values),
};

/** The translator for the chosen language. */
export function useT(): Translate {
  return TRANSLATORS[useLang()];
}
