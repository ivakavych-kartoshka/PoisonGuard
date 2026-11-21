package com.poisonguard.service

data class TrainingStepResult(
    val eventId: String,
    val loss: Float,
    val checkpointHash: String,
    val promoted: Boolean,
    val message: String,
)
