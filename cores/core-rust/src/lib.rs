// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — Rust core library root

//! Standalone Rust core for the Hushline command contract.
//!
//! One of four independent cores. It shares no runtime artefacts with the Go,
//! Python, or Node cores. Its observable behaviour — default profile,
//! configuration merge order, redaction, ANSI stripping, line truncation, and
//! exit codes — matches the Go reference core exactly.

pub mod config;
pub mod engine;
pub mod muter;
pub mod pipeline;

/// Version of the Rust core, kept in lockstep with the other cores.
pub const VERSION: &str = "0.1.5";
