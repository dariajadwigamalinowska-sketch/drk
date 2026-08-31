<?php
/**
 * Plugin Name: Doktor Kasia — bloki stron
 * Description: Arkusze, skrypty i te fragmenty stron, ktore WordPress
 *              usuwa z tresci wpisu (style, skrypty, przyciski, pola
 *              formularza, ikony SVG i ramki iframe). Wtyczka wypisuje
 *              je po stronie serwera, wiec dzialaja niezaleznie od
 *              uprawnien uzytkownika, ktory importowal strony.
 * Version:     1.0.0
 * Author:      Opieka Pediatryczna Doktor Kasi
 * License:     GPL-2.0-or-later
 *
 * PLIK JEST GENEROWANY przez wordpress/build.py — nie poprawiaj go
 * recznie, tylko zrodla w wordpress/*-gutenberg.html i przebuduj.
 */

if ( ! defined( 'ABSPATH' ) ) { exit; }

define( 'DK_WERSJA', '1.0.0' );

/**
 * Arkusze i skrypty. Klasy sa nazwane z przedrostkami (kb- oraz estet),
 * wiec nie mieszaja sie z motywem ani ze soba; kazdy skrypt sam
 * sprawdza, czy jego elementy sa na stronie. Zeby wczytywac je tylko
 * na wybranych stronach, opakuj tresc ponizej warunkiem is_page().
 */
function dk_zasoby() {
	$baza = plugin_dir_url( __FILE__ );
	wp_enqueue_style( 'dk-style-pediatria', $baza . 'style-pediatria.css', array(), DK_WERSJA );
	wp_enqueue_script( 'dk-skrypty-pediatria', $baza . 'skrypty-pediatria.js', array(), DK_WERSJA, true );
	wp_enqueue_style( 'dk-style-medycyna-estetyczna', $baza . 'style-medycyna-estetyczna.css', array(), DK_WERSJA );
	wp_enqueue_script( 'dk-skrypty-estetyczna', $baza . 'skrypty-estetyczna.js', array(), DK_WERSJA, true );
}
add_action( 'wp_enqueue_scripts', 'dk_zasoby' );

/**
 * Wypisuje fragment strony trzymany w pliku obok wtyczki.
 * Nazwa pliku pochodzi wylacznie z kodu ponizej, ale basename()
 * zostaje jako zabezpieczenie na wypadek pozniejszych zmian.
 * Zwracana tresc jest naszym wlasnym kodem strony, wiec nie
 * przepuszczamy jej przez zadne czyszczenie — o to wlasnie chodzi.
 */
function dk_fragment( $plik ) {
	$sciezka = plugin_dir_path( __FILE__ ) . 'fragmenty/' . basename( $plik );
	if ( ! is_readable( $sciezka ) ) {
		return '';
	}
	return file_get_contents( $sciezka );
}

add_shortcode( 'dk_pedi_pasek_profile', function () {
	return dk_fragment( 'dk_pedi_pasek_profile.html' );
} );

add_shortcode( 'dk_pedi_mapa_ramka', function () {
	return dk_fragment( 'dk_pedi_mapa_ramka.html' );
} );

add_shortcode( 'dk_pedi_kalkulator', function () {
	return dk_fragment( 'dk_pedi_kalkulator.html' );
} );

add_shortcode( 'dk_pedi_karuzela', function () {
	return dk_fragment( 'dk_pedi_karuzela.html' );
} );

add_shortcode( 'dk_pedi_spoleczne', function () {
	return dk_fragment( 'dk_pedi_spoleczne.html' );
} );

add_shortcode( 'dk_estet_map', function () {
	return dk_fragment( 'dk_estet_map.html' );
} );
