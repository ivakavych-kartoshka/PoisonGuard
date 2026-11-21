package com.poisonguard.service

/**
 * Minimal provenance tuple for the Android skeleton.
 *
 * This mirrors the paper's event tuple at a high level. Production code must
 * populate these fields from a trusted ingress boundary, not from text producers.
 */
data class ProvenanceEvent(
    val eventId: String,
    val payload: String,
    val channel: String,
    val appId: String,
    val sender: String? = null,
    val userAuthored: Boolean? = null,
    val parentIds: List<String> = emptyList(),
    val metadata: Map<String, String> = emptyMap(),
)
