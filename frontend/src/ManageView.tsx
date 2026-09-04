import { useState } from "react";
import { api } from "./api";
import { CreateForm, Input, Select } from "./form";
import type { Catalogs, InstitutionAnalysis } from "./types";

const blank = (value: string) => (value.trim() === "" ? null : value.trim());

export function ManageView({
  catalogs,
  onChanged,
}: {
  catalogs: Catalogs;
  onChanged: () => void;
}) {
  return (
    <div className="manage">
      <section>
        <h2>Catalog entries</h2>
        <p className="section-hint">
          Shared vocabulary and organizations. Everything else is attached to these.
        </p>
        <div className="form-stack">
          <InstitutionForm onChanged={onChanged} />
          <TypeForm
            title="Instrument type"
            hint="A normalized concept such as Real-Time PCR System."
            create={(payload) => api.createInstrumentType(payload)}
            onChanged={onChanged}
          />
          <TypeForm
            title="Analysis type"
            hint="A normalized concept such as Whole Genome Sequencing."
            create={(payload) => api.createAnalysisType(payload)}
            onChanged={onChanged}
          />
          <MicroorganismForm onChanged={onChanged} />
          <ResearcherForm catalogs={catalogs} onChanged={onChanged} />
        </div>
      </section>

      <section>
        <h2>Institution capabilities</h2>
        <p className="section-hint">
          Concrete instrument units and analysis offerings belonging to one institution.
        </p>
        <div className="form-stack">
          <InstrumentForm catalogs={catalogs} onChanged={onChanged} />
          <AnalysisForm catalogs={catalogs} onChanged={onChanged} />
        </div>
      </section>

      <section>
        <h2>Connections</h2>
        <p className="section-hint">
          An analysis is only searchable through an instrument, organism or researcher once the
          relationship is stated here. Only records from the same institution can be connected.
        </p>
        <ConnectionForms catalogs={catalogs} onChanged={onChanged} />
      </section>
    </div>
  );
}

function InstitutionForm({ onChanged }: { onChanged: () => void }) {
  const [name, setName] = useState("");
  const [city, setCity] = useState("");
  const [country, setCountry] = useState("");
  const [website, setWebsite] = useState("");
  const [email, setEmail] = useState("");
  const [description, setDescription] = useState("");
  const [address, setAddress] = useState("");

  return (
    <CreateForm
      title="Institution"
      hint="The slug comes from the name when left empty. The address is looked up to place the institution on a map."
      submitLabel="Create institution"
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
          ? `Created ${created.name}, but the address could not be placed on a map`
          : `Created ${created.name}`;
      }}
    >
      <Input label="Name" value={name} onChange={setName} required />
      <Input
        label="Street address"
        value={address}
        onChange={setAddress}
        placeholder="Bulevar oslobodjenja 18"
      />
      <Input label="City" value={city} onChange={setCity} required />
      <Input label="Country" value={country} onChange={setCountry} required />
      <Input label="Website" value={website} onChange={setWebsite} />
      <Input label="Contact email" value={email} onChange={setEmail} type="email" />
      <Input label="Description" value={description} onChange={setDescription} />
    </CreateForm>
  );
}

function TypeForm({
  title,
  hint,
  create,
  onChanged,
}: {
  title: string;
  hint: string;
  create: (payload: unknown) => Promise<{ name: string }>;
  onChanged: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  return (
    <CreateForm
      title={title}
      hint={hint}
      submitLabel={`Create ${title.toLowerCase()}`}
      onDone={onChanged}
      onSubmit={async () => {
        const created = await create({ name, description: blank(description) });
        setName("");
        setDescription("");
        return `Created ${created.name}`;
      }}
    >
      <Input label="Name" value={name} onChange={setName} required />
      <Input label="Description" value={description} onChange={setDescription} />
    </CreateForm>
  );
}

function MicroorganismForm({ onChanged }: { onChanged: () => void }) {
  const [scientificName, setScientificName] = useState("");
  const [commonName, setCommonName] = useState("");
  const [description, setDescription] = useState("");

  return (
    <CreateForm
      title="Target organism"
      hint="A microorganism an analysis can detect, identify or otherwise process."
      submitLabel="Create organism"
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
        return `Created ${created.scientific_name}`;
      }}
    >
      <Input
        label="Scientific name"
        value={scientificName}
        onChange={setScientificName}
        required
      />
      <Input label="Common name" value={commonName} onChange={setCommonName} />
      <Input label="Description" value={description} onChange={setDescription} />
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
  const [institutionId, setInstitutionId] = useState("");
  const [fullName, setFullName] = useState("");
  const [title, setTitle] = useState("");
  const [email, setEmail] = useState("");
  const [orcid, setOrcid] = useState("");
  const [expertise, setExpertise] = useState("");

  return (
    <CreateForm
      title="Researcher"
      hint="A researcher belongs to exactly one institution."
      submitLabel="Create researcher"
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
        return `Created ${created.full_name}`;
      }}
    >
      <Select
        label="Institution"
        value={institutionId}
        onChange={setInstitutionId}
        placeholder="Select an institution"
        required
      >
        {catalogs.institutions.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </Select>
      <Input label="Full name" value={fullName} onChange={setFullName} required />
      <Input label="Title" value={title} onChange={setTitle} placeholder="Research Associate" />
      <Input label="Email" value={email} onChange={setEmail} type="email" />
      <Input label="ORCID" value={orcid} onChange={setOrcid} placeholder="0000-0002-…" />
      <Input label="Expertise" value={expertise} onChange={setExpertise} />
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
  const [institutionId, setInstitutionId] = useState("");
  const [typeId, setTypeId] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [manufacturer, setManufacturer] = useState("");
  const [model, setModel] = useState("");
  const [status, setStatus] = useState("operational");

  return (
    <CreateForm
      title="Institution instrument"
      hint="A concrete instrument unit owned by one institution."
      submitLabel="Create instrument"
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
        return "Instrument added to the institution";
      }}
    >
      <Select
        label="Institution"
        value={institutionId}
        onChange={setInstitutionId}
        placeholder="Select an institution"
        required
      >
        {catalogs.institutions.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </Select>
      <Select
        label="Instrument type"
        value={typeId}
        onChange={setTypeId}
        placeholder="Select a type"
        required
      >
        {catalogs.instrumentTypes.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </Select>
      <Input label="Display name" value={displayName} onChange={setDisplayName} />
      <Input label="Manufacturer" value={manufacturer} onChange={setManufacturer} />
      <Input label="Model" value={model} onChange={setModel} />
      <Select label="Status" value={status} onChange={setStatus} placeholder={null}>
        <option value="operational">operational</option>
        <option value="maintenance">maintenance</option>
        <option value="unavailable">unavailable</option>
        <option value="archived">archived</option>
      </Select>
    </CreateForm>
  );
}

function AnalysisForm({ catalogs, onChanged }: { catalogs: Catalogs; onChanged: () => void }) {
  const [institutionId, setInstitutionId] = useState("");
  const [typeId, setTypeId] = useState("");
  const [publicName, setPublicName] = useState("");
  const [turnaround, setTurnaround] = useState("");
  const [availability, setAvailability] = useState("available");
  const [description, setDescription] = useState("");

  return (
    <CreateForm
      title="Institution analysis"
      hint="A concrete service offered by one institution. One offering per analysis type."
      submitLabel="Create analysis offering"
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
        return "Analysis offering created";
      }}
    >
      <Select
        label="Institution"
        value={institutionId}
        onChange={setInstitutionId}
        placeholder="Select an institution"
        required
      >
        {catalogs.institutions.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </Select>
      <Select
        label="Analysis type"
        value={typeId}
        onChange={setTypeId}
        placeholder="Select a type"
        required
      >
        {catalogs.analysisTypes.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </Select>
      <Input label="Public name" value={publicName} onChange={setPublicName} />
      <Input
        label="Turnaround days"
        value={turnaround}
        onChange={setTurnaround}
        type="number"
        placeholder="optional"
      />
      <Select
        label="Availability"
        value={availability}
        onChange={setAvailability}
        placeholder={null}
      >
        <option value="available">available</option>
        <option value="limited">limited</option>
        <option value="unavailable">unavailable</option>
        <option value="archived">archived</option>
      </Select>
      <Input label="Description" value={description} onChange={setDescription} />
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
  const [analysisId, setAnalysisId] = useState("");
  const analysis = catalogs.institutionAnalyses.find(
    (item) => String(item.id) === analysisId,
  );

  const analysisLabel = (item: InstitutionAnalysis) => {
    const institution = catalogs.institutions.find((entry) => entry.id === item.institution_id);
    const type = catalogs.analysisTypes.find((entry) => entry.id === item.analysis_type_id);
    return `${institution?.name ?? `Institution ${item.institution_id}`} — ${
      item.public_name || type?.name || `Analysis ${item.id}`
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
          label="Analysis offering to connect"
          value={analysisId}
          onChange={setAnalysisId}
          placeholder="Select an analysis offering"
        >
          {catalogs.institutionAnalyses.map((item) => (
            <option key={item.id} value={item.id}>
              {analysisLabel(item)}
            </option>
          ))}
        </Select>
      </div>

      {!analysis ? (
        <p className="empty">Select an analysis offering to connect it to other records.</p>
      ) : (
        <div className="form-stack">
          <LinkForm
            title="Use an instrument"
            hint="Only instruments owned by the same institution can be used."
            submitLabel="Link instrument"
            options={ownInstruments.map((item) => ({
              value: String(item.id),
              label: `${item.display_name || `Instrument ${item.id}`} (${item.status})`,
            }))}
            optionLabel="Instrument"
            optionPlaceholder="Select an instrument"
            emptyMessage="This institution has no instruments yet."
            roles={["required", "optional", "alternative"]}
            roleLabel="Usage"
            onSubmit={(id, usage) =>
              api
                .linkInstrument(analysis.id, {
                  institution_instrument_id: Number(id),
                  usage,
                })
                .then(() => "Instrument linked")
            }
            onChanged={onChanged}
          />
          <LinkForm
            title="Detect a target organism"
            hint="States that this offering can process the organism."
            submitLabel="Link organism"
            options={catalogs.microorganisms.map((item) => ({
              value: String(item.id),
              label: item.scientific_name,
            }))}
            optionLabel="Target organism"
            optionPlaceholder="Select a target organism"
            emptyMessage="No organisms in the catalog yet."
            onSubmit={(id) =>
              api
                .linkTarget(analysis.id, { microorganism_id: Number(id) })
                .then(() => "Target organism linked")
            }
            onChanged={onChanged}
          />
          <LinkForm
            title="Assign a researcher"
            hint="Only researchers of the same institution can be assigned."
            submitLabel="Link researcher"
            options={ownResearchers.map((item) => ({
              value: String(item.id),
              label: item.title ? `${item.full_name} — ${item.title}` : item.full_name,
            }))}
            optionLabel="Researcher"
            optionPlaceholder="Select a researcher"
            emptyMessage="This institution has no researchers yet."
            roles={["lead", "contributor", "contact"]}
            roleLabel="Role"
            onSubmit={(id, role) =>
              api
                .linkResearcher(analysis.id, { researcher_id: Number(id), role })
                .then(() => "Researcher linked")
            }
            onChanged={onChanged}
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
  options,
  optionLabel,
  optionPlaceholder,
  emptyMessage,
  roles,
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
  roles?: string[];
  roleLabel?: string;
  onSubmit: (id: string, role: string) => Promise<string>;
  onChanged: () => void;
}) {
  const [selected, setSelected] = useState("");
  const [role, setRole] = useState(roles?.[0] ?? "");

  if (options.length === 0) {
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
        {options.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </Select>
      {roles && (
        <Select label={roleLabel ?? "Role"} value={role} onChange={setRole} placeholder={null}>
          {roles.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </Select>
      )}
    </CreateForm>
  );
}
