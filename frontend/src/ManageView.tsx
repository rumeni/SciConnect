import { useState } from "react";
import { api } from "./api";
import { CreateForm, Input, Select } from "./form";
import { useT, type MessageKey, type Translate } from "./i18n";
import { CurrentConnections, RemoveRecordForm } from "./Removal";
import type { Catalogs, InstitutionAnalysis } from "./types";

const blank = (value: string) => (value.trim() === "" ? null : value.trim());

export function ManageView({
  catalogs,
  onChanged,
}: {
  catalogs: Catalogs;
  onChanged: () => void;
}) {
  const t = useT();

  return (
    <div className="manage">
      <section>
        <h2>{t("manage.catalog")}</h2>
        <p className="section-hint">{t("manage.catalog.hint")}</p>
        <div className="form-stack">
          <InstitutionForm onChanged={onChanged} />
          <TypeForm
            title={t("manage.instrumentType.title")}
            hint={t("manage.instrumentType.hint")}
            submitLabel={t("manage.instrumentType.submit")}
            create={(payload) => api.createInstrumentType(payload)}
            onChanged={onChanged}
          />
          <TypeForm
            title={t("manage.analysisType.title")}
            hint={t("manage.analysisType.hint")}
            submitLabel={t("manage.analysisType.submit")}
            create={(payload) => api.createAnalysisType(payload)}
            onChanged={onChanged}
          />
          <MicroorganismForm onChanged={onChanged} />
          <ResearcherForm catalogs={catalogs} onChanged={onChanged} />
        </div>
      </section>

      <section>
        <h2>{t("manage.capabilities")}</h2>
        <p className="section-hint">{t("manage.capabilities.hint")}</p>
        <div className="form-stack">
          <InstrumentForm catalogs={catalogs} onChanged={onChanged} />
          <AnalysisForm catalogs={catalogs} onChanged={onChanged} />
        </div>
      </section>

      <section>
        <h2>{t("manage.connections")}</h2>
        <p className="section-hint">{t("manage.connections.hint")}</p>
        <ConnectionForms catalogs={catalogs} onChanged={onChanged} />
      </section>

      <section>
        <h2>{t("manage.removing")}</h2>
        <p className="section-hint">{t("manage.removing.hint")}</p>
        <div className="form-stack">
          <RemoveRecordForm catalogs={catalogs} onChanged={onChanged} />
        </div>
      </section>
    </div>
  );
}

/** The fixed vocabulary a select offers, each option named in both languages. */
function options(t: Translate, keys: MessageKey[], values: string[]) {
  return values.map((value, index) => (
    <option key={value} value={value}>
      {t(keys[index])}
    </option>
  ));
}

function InstitutionForm({ onChanged }: { onChanged: () => void }) {
  const t = useT();
  const [name, setName] = useState("");
  const [city, setCity] = useState("");
  const [country, setCountry] = useState("");
  const [website, setWebsite] = useState("");
  const [email, setEmail] = useState("");
  const [description, setDescription] = useState("");
  const [address, setAddress] = useState("");

  return (
    <CreateForm
      title={t("manage.institution.title")}
      hint={t("manage.institution.hint")}
      submitLabel={t("manage.institution.submit")}
      onDone={onChanged}
      onSubmit={async () => {
        const created = await api.createInstitution({
          name,
          city,
          country,
          address: blank(address),
          website: blank(website),
          contact_email: blank(email),
          description: blank(description),
        });
        setName("");
        setCity("");
        setCountry("");
        setAddress("");
        setWebsite("");
        setEmail("");
        setDescription("");
        return created.latitude === null
          ? t("manage.institution.createdNoMap", { name: created.name })
          : t("manage.institution.created", { name: created.name });
      }}
    >
      <Input label={t("manage.field.name")} value={name} onChange={setName} required />
      <Input
        label={t("manage.field.address")}
        value={address}
        onChange={setAddress}
        placeholder={t("manage.field.addressPlaceholder")}
      />
      <Input label={t("manage.field.city")} value={city} onChange={setCity} required />
      <Input label={t("manage.field.country")} value={country} onChange={setCountry} required />
      <Input label={t("manage.field.website")} value={website} onChange={setWebsite} />
      <Input
        label={t("manage.field.contactEmail")}
        value={email}
        onChange={setEmail}
        type="email"
      />
      <Input
        label={t("manage.field.description")}
        value={description}
        onChange={setDescription}
      />
    </CreateForm>
  );
}

function TypeForm({
  title,
  hint,
  submitLabel,
  create,
  onChanged,
}: {
  title: string;
  hint: string;
  submitLabel: string;
  create: (payload: unknown) => Promise<{ name: string }>;
  onChanged: () => void;
}) {
  const t = useT();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  return (
    <CreateForm
      title={title}
      hint={hint}
      submitLabel={submitLabel}
      onDone={onChanged}
      onSubmit={async () => {
        const created = await create({ name, description: blank(description) });
        setName("");
        setDescription("");
        return t("manage.created", { name: created.name });
      }}
    >
      <Input label={t("manage.field.name")} value={name} onChange={setName} required />
      <Input
        label={t("manage.field.description")}
        value={description}
        onChange={setDescription}
      />
    </CreateForm>
  );
}

function MicroorganismForm({ onChanged }: { onChanged: () => void }) {
  const t = useT();
  const [scientificName, setScientificName] = useState("");
  const [commonName, setCommonName] = useState("");
  const [description, setDescription] = useState("");

  return (
    <CreateForm
      title={t("manage.organism.title")}
      hint={t("manage.organism.hint")}
      submitLabel={t("manage.organism.submit")}
      onDone={onChanged}
      onSubmit={async () => {
        const created = await api.createMicroorganism({
          scientific_name: scientificName,
          common_name: blank(commonName),
          description: blank(description),
        });
        setScientificName("");
        setCommonName("");
        setDescription("");
        return t("manage.created", { name: created.scientific_name });
      }}
    >
      <Input
        label={t("manage.field.scientificName")}
        value={scientificName}
        onChange={setScientificName}
        required
      />
      <Input
        label={t("manage.field.commonName")}
        value={commonName}
        onChange={setCommonName}
      />
      <Input
        label={t("manage.field.description")}
        value={description}
        onChange={setDescription}
      />
    </CreateForm>
  );
}

function ResearcherForm({
  catalogs,
  onChanged,
}: {
  catalogs: Catalogs;
  onChanged: () => void;
}) {
  const t = useT();
  const [institutionId, setInstitutionId] = useState("");
  const [fullName, setFullName] = useState("");
  const [title, setTitle] = useState("");
  const [email, setEmail] = useState("");
  const [orcid, setOrcid] = useState("");
  const [expertise, setExpertise] = useState("");

  return (
    <CreateForm
      title={t("manage.researcher.title")}
      hint={t("manage.researcher.hint")}
      submitLabel={t("manage.researcher.submit")}
      onDone={onChanged}
      onSubmit={async () => {
        const created = await api.createResearcher({
          institution_id: Number(institutionId),
          full_name: fullName,
          title: blank(title),
          email: blank(email),
          orcid: blank(orcid),
          expertise: blank(expertise),
        });
        setFullName("");
        setTitle("");
        setEmail("");
        setOrcid("");
        setExpertise("");
        return t("manage.created", { name: created.full_name });
      }}
    >
      <Select
        label={t("manage.field.institution")}
        value={institutionId}
        onChange={setInstitutionId}
        placeholder={t("manage.pick.institution")}
        required
      >
        {catalogs.institutions.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </Select>
      <Input
        label={t("manage.field.fullName")}
        value={fullName}
        onChange={setFullName}
        required
      />
      <Input
        label={t("manage.field.title")}
        value={title}
        onChange={setTitle}
        placeholder={t("manage.field.titlePlaceholder")}
      />
      <Input label={t("manage.field.email")} value={email} onChange={setEmail} type="email" />
      <Input
        label={t("manage.field.orcid")}
        value={orcid}
        onChange={setOrcid}
        placeholder="0000-0002-…"
      />
      <Input
        label={t("manage.field.expertise")}
        value={expertise}
        onChange={setExpertise}
      />
    </CreateForm>
  );
}

function InstrumentForm({
  catalogs,
  onChanged,
}: {
  catalogs: Catalogs;
  onChanged: () => void;
}) {
  const t = useT();
  const [institutionId, setInstitutionId] = useState("");
  const [typeId, setTypeId] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [manufacturer, setManufacturer] = useState("");
  const [model, setModel] = useState("");
  const [status, setStatus] = useState("operational");

  return (
    <CreateForm
      title={t("manage.instrument.title")}
      hint={t("manage.instrument.hint")}
      submitLabel={t("manage.instrument.submit")}
      onDone={onChanged}
      onSubmit={async () => {
        await api.createInstitutionInstrument({
          institution_id: Number(institutionId),
          instrument_type_id: Number(typeId),
          display_name: blank(displayName),
          manufacturer: blank(manufacturer),
          model: blank(model),
          status,
        });
        setDisplayName("");
        setManufacturer("");
        setModel("");
        return t("manage.instrument.created");
      }}
    >
      <Select
        label={t("manage.field.institution")}
        value={institutionId}
        onChange={setInstitutionId}
        placeholder={t("manage.pick.institution")}
        required
      >
        {catalogs.institutions.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </Select>
      <Select
        label={t("manage.field.instrumentType")}
        value={typeId}
        onChange={setTypeId}
        placeholder={t("manage.pick.type")}
        required
      >
        {catalogs.instrumentTypes.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </Select>
      <Input
        label={t("manage.field.displayName")}
        value={displayName}
        onChange={setDisplayName}
      />
      <Input
        label={t("manage.field.manufacturer")}
        value={manufacturer}
        onChange={setManufacturer}
      />
      <Input label={t("manage.field.model")} value={model} onChange={setModel} />
      <Select
        label={t("manage.field.status")}
        value={status}
        onChange={setStatus}
        placeholder={null}
      >
        {options(
          t,
          ["status.operational", "status.maintenance", "status.unavailable", "status.archived"],
          ["operational", "maintenance", "unavailable", "archived"],
        )}
      </Select>
    </CreateForm>
  );
}

function AnalysisForm({ catalogs, onChanged }: { catalogs: Catalogs; onChanged: () => void }) {
  const t = useT();
  const [institutionId, setInstitutionId] = useState("");
  const [typeId, setTypeId] = useState("");
  const [publicName, setPublicName] = useState("");
  const [turnaround, setTurnaround] = useState("");
  const [availability, setAvailability] = useState("available");
  const [description, setDescription] = useState("");

  return (
    <CreateForm
      title={t("manage.analysis.title")}
      hint={t("manage.analysis.hint")}
      submitLabel={t("manage.analysis.submit")}
      onDone={onChanged}
      onSubmit={async () => {
        await api.createInstitutionAnalysis({
          institution_id: Number(institutionId),
          analysis_type_id: Number(typeId),
          public_name: blank(publicName),
          description: blank(description),
          turnaround_days: turnaround === "" ? null : Number(turnaround),
          availability,
        });
        setPublicName("");
        setTurnaround("");
        setDescription("");
        return t("manage.analysis.created");
      }}
    >
      <Select
        label={t("manage.field.institution")}
        value={institutionId}
        onChange={setInstitutionId}
        placeholder={t("manage.pick.institution")}
        required
      >
        {catalogs.institutions.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </Select>
      <Select
        label={t("manage.field.analysisType")}
        value={typeId}
        onChange={setTypeId}
        placeholder={t("manage.pick.type")}
        required
      >
        {catalogs.analysisTypes.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </Select>
      <Input
        label={t("manage.field.publicName")}
        value={publicName}
        onChange={setPublicName}
      />
      <Input
        label={t("manage.field.turnaround")}
        value={turnaround}
        onChange={setTurnaround}
        type="number"
        placeholder={t("manage.field.optional")}
      />
      <Select
        label={t("manage.field.availability")}
        value={availability}
        onChange={setAvailability}
        placeholder={null}
      >
        {options(
          t,
          ["status.available", "status.limited", "status.unavailable", "status.archived"],
          ["available", "limited", "unavailable", "archived"],
        )}
      </Select>
      <Input
        label={t("manage.field.description")}
        value={description}
        onChange={setDescription}
      />
    </CreateForm>
  );
}

function ConnectionForms({
  catalogs,
  onChanged,
}: {
  catalogs: Catalogs;
  onChanged: () => void;
}) {
  const t = useT();
  const [analysisId, setAnalysisId] = useState("");
  // Adding a connection has to reach the list of current connections too, which
  // reads the offering directly rather than through the shared catalogs.
  const [linkVersion, setLinkVersion] = useState(0);
  const noteChange = () => {
    setLinkVersion((count) => count + 1);
    onChanged();
  };
  const analysis = catalogs.institutionAnalyses.find(
    (item) => String(item.id) === analysisId,
  );

  const analysisLabel = (item: InstitutionAnalysis) => {
    const institution = catalogs.institutions.find((entry) => entry.id === item.institution_id);
    const type = catalogs.analysisTypes.find((entry) => entry.id === item.analysis_type_id);
    return `${
      institution?.name ?? t("connect.unnamedInstitution", { id: item.institution_id })
    } — ${
      item.public_name || type?.name || t("connect.unnamedAnalysis", { id: item.id })
    }`;
  };

  const ownInstruments = catalogs.institutionInstruments.filter(
    (item) => analysis && item.institution_id === analysis.institution_id,
  );
  const ownResearchers = catalogs.researchers.filter(
    (item) => analysis && item.institution_id === analysis.institution_id,
  );

  return (
    <>
      <div className="picker">
        <Select
          label={t("connect.picker")}
          value={analysisId}
          onChange={setAnalysisId}
          placeholder={t("manage.pick.offering")}
        >
          {catalogs.institutionAnalyses.map((item) => (
            <option key={item.id} value={item.id}>
              {analysisLabel(item)}
            </option>
          ))}
        </Select>
      </div>

      {!analysis ? (
        <p className="empty">{t("connect.pickFirst")}</p>
      ) : (
        <div className="form-stack">
          <LinkForm
            title={t("connect.instrument.title")}
            hint={t("connect.instrument.hint")}
            submitLabel={t("connect.instrument.submit")}
            options={ownInstruments.map((item) => ({
              value: String(item.id),
              label: `${
                item.display_name || t("connect.unnamedInstrument", { id: item.id })
              } (${item.status})`,
            }))}
            optionLabel={t("search.instrument")}
            optionPlaceholder={t("manage.pick.instrument")}
            emptyMessage={t("connect.instrument.empty")}
            roles={["required", "optional", "alternative"]}
            roleKeys={["role.required", "role.optional", "role.alternative"]}
            roleLabel={t("manage.field.usage")}
            onSubmit={(id, usage) =>
              api
                .linkInstrument(analysis.id, {
                  institution_instrument_id: Number(id),
                  usage,
                })
                .then(() => t("connect.instrument.done"))
            }
            onChanged={noteChange}
          />
          <LinkForm
            title={t("connect.organism.title")}
            hint={t("connect.organism.hint")}
            submitLabel={t("connect.organism.submit")}
            options={catalogs.microorganisms.map((item) => ({
              value: String(item.id),
              label: item.scientific_name,
            }))}
            optionLabel={t("search.organism")}
            optionPlaceholder={t("manage.pick.organism")}
            emptyMessage={t("connect.organism.empty")}
            onSubmit={(id) =>
              api
                .linkTarget(analysis.id, { microorganism_id: Number(id) })
                .then(() => t("connect.organism.done"))
            }
            onChanged={noteChange}
          />
          <LinkForm
            title={t("connect.researcher.title")}
            hint={t("connect.researcher.hint")}
            submitLabel={t("connect.researcher.submit")}
            options={ownResearchers.map((item) => ({
              value: String(item.id),
              label: item.title ? `${item.full_name} — ${item.title}` : item.full_name,
            }))}
            optionLabel={t("search.researcher")}
            optionPlaceholder={t("manage.pick.researcher")}
            emptyMessage={t("connect.researcher.empty")}
            roles={["lead", "contributor", "contact"]}
            roleKeys={["role.lead", "role.contributor", "role.contact"]}
            roleLabel={t("manage.field.role")}
            onSubmit={(id, role) =>
              api
                .linkResearcher(analysis.id, { researcher_id: Number(id), role })
                .then(() => t("connect.researcher.done"))
            }
            onChanged={noteChange}
          />
          <CurrentConnections
            analysisId={analysis.id}
            version={linkVersion}
            onChanged={noteChange}
          />
        </div>
      )}
    </>
  );
}

function LinkForm({
  title,
  hint,
  submitLabel,
  options: choices,
  optionLabel,
  optionPlaceholder,
  emptyMessage,
  roles,
  roleKeys,
  roleLabel,
  onSubmit,
  onChanged,
}: {
  title: string;
  hint: string;
  submitLabel: string;
  options: { value: string; label: string }[];
  optionLabel: string;
  optionPlaceholder: string;
  emptyMessage: string;
  /** The values the API expects, which are never translated. */
  roles?: string[];
  /** How each of those values is shown, in the same order. */
  roleKeys?: MessageKey[];
  roleLabel?: string;
  onSubmit: (id: string, role: string) => Promise<string>;
  onChanged: () => void;
}) {
  const t = useT();
  const [selected, setSelected] = useState("");
  const [role, setRole] = useState(roles?.[0] ?? "");

  if (choices.length === 0) {
    return (
      <div className="card-form">
        <h3>{title}</h3>
        <p className="empty">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <CreateForm
      title={title}
      hint={hint}
      submitLabel={submitLabel}
      onDone={onChanged}
      onSubmit={async () => {
        const message = await onSubmit(selected, role);
        setSelected("");
        return message;
      }}
    >
      <Select
        label={optionLabel}
        value={selected}
        onChange={setSelected}
        placeholder={optionPlaceholder}
        required
      >
        {choices.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </Select>
      {roles && (
        <Select
          label={roleLabel ?? t("manage.field.role")}
          value={role}
          onChange={setRole}
          placeholder={null}
        >
          {roles.map((item, index) => (
            <option key={item} value={item}>
              {roleKeys ? t(roleKeys[index]) : item}
            </option>
          ))}
        </Select>
      )}
    </CreateForm>
  );
}
