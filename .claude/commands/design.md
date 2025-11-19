---
allowed-tools: Glob, Grep, Read, Task, Write, Edit, LS, WebSearch
argument-hint: feature to design
description: Create or update the design document for a specific feature.
---

# Rule

The `<execute>ARGUMENTS</execute>` will execute the main procedure.

# Role

You are an expert software architect and experienced in technical documentation. Your task is to create or update design documents for specific feature to ensure clarity and coherence in the implementation process.

# Definition

<function name="search">
    <description>Search the spec document for the given feature name to extract relevant details.</description>
    <parameter name="feature_name" type="string">The name of the feature to search for.</parameter>
    <step>1. Check ./docs/features/ for a markdown file that matches the feature name.</step>
    <condition if="found">
        <return>Return the path to the feature spec document.</return>
    </condition>
    <step>2. Use AskUserQuestion tool to ask the user for the correct feature name or path.</step>
    <return>Return the user-provided path.</return>
</function>

<procedure name="research">
    <description>Research the codebase to gather necessary information for the design document.</description>
    <parameter name="related_components" type="list">List of related components will be implemented in the feature.</parameter>
    <step>1. Read documents in ./docs/ARCHITECTURE.md to understand the overall architecture.</step>
    <step>2. Read documents in ./docs/entities.md to understand the domain entities, reuse if already exists.</step>
    <condition if="entities involved">
        <step>3. Identify and list the entities involved in the feature from the feature spec document.</step>
    </condition>
    <loop over="related_components" as="component" parallel="true">
        <step>4. Check the codebase for files and modules related to {component} use Task tool in parallel</step>
        <step>5. For libraries or external dependencies, use WebSearch tool to help gather information. Use official documentation and reputable sources only.</step>
        <step>6. Extract relevant information about {component} and its interactions.</step>
    </loop>
    <return>Return the gathered information for inclusion in the design document.</return>
</procedure>

<procedure name="main">
    <description>Create or update the design document for a specific feature.</description>
    <parameter name="feature_name" type="string">The name of the feature to design.</parameter>
    <step>1. <execute name="search">{feature_name}</execute> to get the path to the feature spec document.</step>
    <condition if="design not exists">
        <step>2. Create a new design document at ./docs/design/ using the template from ./docs/template/design.md.</step>
    </condition>
    <step>3. Read the feature spec document to extract details about the feature.</step>
    <step>4. Identify related components and entities involved in the feature.</step>
    <step>5. <execute name="research">related_components</execute> to gather necessary information.</step>
    <step>6. Populate the design document with the gathered information, ensuring clarity and coherence.</step>
    <condition if="entities involved">
        <step>7. Update the ./docs/entities.md to include or modify the entities related to the feature.</step>
    </condition>
    <step>7. Review the design document for completeness and accuracy.</step>
    <step>8. Save the updated design document.</step>
</procedure>

# Task

<execute name="main">$ARGUMENTS</execute>
