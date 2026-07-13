#!/usr/bin/env bash
set -euo pipefail

# Finalize the installed system without evaluating data from the live kernel
# command line or following attacker-controlled files from /tmp.

readonly max_live_config_bytes=$((16 * 1024 * 1024))
readonly live_state_directory=/run/biglinux-live
declare -a temporary_files=()
created_temporary_file=
root_mount=

cleanup_temporary_files() {
	local temporary_file
	for temporary_file in "${temporary_files[@]}"; do
		[[ -n $temporary_file ]] && rm -f -- "$temporary_file"
	done
	return 0
}

trap cleanup_temporary_files EXIT
trap 'exit 1' HUP INT TERM

die() {
	printf 'biglinux-install-setup: %s\n' "$*" >&2
	exit 1
}

load_kernel_options() {
	local installed_library=/usr/lib/biglinux-livecd/kernel-options
	local script_directory development_library
	if [[ -r $installed_library ]]; then
		# shellcheck disable=SC1090,SC1091
		source "$installed_library"
		return
	fi
	script_directory=$(realpath -e -- "$(dirname -- "${BASH_SOURCE[0]}")") || return 1
	development_library=$(realpath -e -- "$script_directory/../lib/biglinux-livecd/kernel-options") || return 1
	# shellcheck disable=SC1090,SC1091
	source "$development_library"
}

canonical_root_mount() {
	local requested=${1:-} resolved
	[[ -n $requested && -d $requested ]] || die "invalid root mount point: $requested"
	resolved=$(realpath -e -- "$requested") || die "cannot resolve root mount point: $requested"
	[[ $resolved != / ]] || die 'refusing to modify the running root filesystem'
	printf '%s\n' "$resolved"
}

path_is_within_root() {
	local resolved=$1
	[[ $resolved == "$root_mount" || $resolved == "$root_mount/"* ]]
}

ensure_directory() {
	local directory=$1 mode=${2:-0755}
	local resolved
	resolved=$(realpath -m -- "$directory") || die "cannot resolve directory: $directory"
	path_is_within_root "$resolved" || die "directory escapes installation root: $directory"
	install -d -m "$mode" -- "$directory"
	resolved=$(realpath -e -- "$directory") || die "cannot verify directory: $directory"
	path_is_within_root "$resolved" || die "directory escapes installation root: $directory"
}

make_temporary_file() {
	local target=$1 parent base temporary_file
	parent=$(dirname -- "$target")
	base=$(basename -- "$target")
	[[ -d $parent && ! -L $parent ]] || die "unsafe destination directory: $parent"
	temporary_file=$(mktemp -- "$parent/.${base}.XXXXXX") || die "cannot create temporary file for $target"
	temporary_files+=("$temporary_file")
	created_temporary_file=$temporary_file
}

forget_temporary_file() {
	local completed=$1 index
	for index in "${!temporary_files[@]}"; do
		if [[ ${temporary_files[$index]} == "$completed" ]]; then
			temporary_files[index]=
			return
		fi
	done
}

commit_temporary_file() {
	local temporary_file=$1 target=$2 mode=$3
	local owner group parent
	[[ ! -L $target ]] || die "refusing symbolic-link destination: $target"
	parent=$(dirname -- "$target")
	if [[ -e $target ]]; then
		[[ -f $target ]] || die "destination is not a regular file: $target"
		owner=$(stat -c '%u' -- "$target")
		group=$(stat -c '%g' -- "$target")
	else
		owner=$(stat -c '%u' -- "$parent")
		group=$(stat -c '%g' -- "$parent")
	fi
	chmod "$mode" -- "$temporary_file"
	chown "$owner:$group" -- "$temporary_file"
	sync -f -- "$temporary_file"
	mv -fT -- "$temporary_file" "$target"
	forget_temporary_file "$temporary_file"
	sync -f -- "$parent"
}

trim_whitespace() {
	local value=$1
	value=${value#"${value%%[![:space:]]*}"}
	value=${value%"${value##*[![:space:]]}"}
	printf '%s\n' "$value"
}

decode_double_quoted_value() {
	local value=$1 decoded='' character next
	local index
	for ((index = 0; index < ${#value}; index++)); do
		character=${value:index:1}
		if [[ $character == \\ && $((index + 1)) -lt ${#value} ]]; then
			next=${value:index+1:1}
			# The single-character patterns are literal shell escapes.
			# shellcheck disable=SC1003
			case "$next" in
			'\\' | '"' | '$' | '`')
				decoded+=$next
				index=$((index + 1))
				continue
				;;
			esac
		fi
		decoded+=$character
	done
	printf '%s\n' "$decoded"
}

decode_grub_value() {
	local value
	value=$(trim_whitespace "$1")
	if [[ ${#value} -ge 2 && ${value:0:1} == '"' && ${value: -1} == '"' ]]; then
		decode_double_quoted_value "${value:1:${#value}-2}"
	elif [[ ${#value} -ge 2 && ${value:0:1} == "'" && ${value: -1} == "'" ]]; then
		printf '%s\n' "${value:1:${#value}-2}"
	else
		printf '%s\n' "$value"
	fi
}

escape_grub_double_quoted_value() {
	local value=$1
	value=${value//\\/\\\\}
	value=${value//\"/\\\"}
	value=${value//\$/\\\$}
	value=${value//\`/\\\`}
	printf '%s\n' "$value"
}

current_grub_kernel_arguments() {
	local grub_file=$1 line value=
	local matches=0
	while IFS= read -r line || [[ -n $line ]]; do
		if [[ $line =~ ^[[:space:]]*GRUB_CMDLINE_LINUX_DEFAULT[[:space:]]*=(.*)$ ]]; then
			matches=$((matches + 1))
			value=${BASH_REMATCH[1]}
		fi
	done <"$grub_file"
	((matches <= 1)) || die "ambiguous GRUB_CMDLINE_LINUX_DEFAULT entries in $grub_file"
	decode_grub_value "$value"
}

write_grub_configuration() {
	local grub_file=$1 existing_arguments live_arguments combined_arguments escaped_arguments
	local temporary_file line
	local wrote_arguments=0 wrote_savedefault=0 has_early_initrd=0
	[[ -f $grub_file && ! -L $grub_file ]] || die "unsafe GRUB configuration: $grub_file"
	existing_arguments=$(current_grub_kernel_arguments "$grub_file")
	live_arguments=$(installed_kernel_arguments) || die 'cannot read live kernel arguments'
	combined_arguments=$(sanitize_installed_kernel_arguments "$existing_arguments $live_arguments")
	escaped_arguments=$(escape_grub_double_quoted_value "$combined_arguments")
	make_temporary_file "$grub_file"
	temporary_file=$created_temporary_file
	while IFS= read -r line || [[ -n $line ]]; do
		if [[ $line =~ ^[[:space:]]*GRUB_CMDLINE_LINUX_DEFAULT[[:space:]]*= ]]; then
			if ((wrote_arguments == 0)); then
				printf 'GRUB_CMDLINE_LINUX_DEFAULT="%s"\n' "$escaped_arguments" >>"$temporary_file"
				wrote_arguments=1
			fi
		elif [[ $line =~ ^[[:space:]]*GRUB_SAVEDEFAULT[[:space:]]*= ]]; then
			if ((wrote_savedefault == 0)); then
				printf 'GRUB_SAVEDEFAULT=false\n' >>"$temporary_file"
				wrote_savedefault=1
			fi
		else
			printf '%s\n' "$line" >>"$temporary_file"
			[[ $line =~ ^[[:space:]]*GRUB_EARLY_INITRD_LINUX_STOCK[[:space:]]*= ]] && has_early_initrd=1
		fi
	done <"$grub_file"
	((wrote_arguments == 1)) || printf 'GRUB_CMDLINE_LINUX_DEFAULT="%s"\n' "$escaped_arguments" >>"$temporary_file"
	((wrote_savedefault == 1)) || printf 'GRUB_SAVEDEFAULT=false\n' >>"$temporary_file"
	((has_early_initrd == 1)) || printf "GRUB_EARLY_INITRD_LINUX_STOCK=''\n" >>"$temporary_file"
	commit_temporary_file "$temporary_file" "$grub_file" "$(stat -c '%a' -- "$grub_file")"
}

atomic_write_text() {
	local target=$1 mode=$2 text=$3 temporary_file
	ensure_directory "$(dirname -- "$target")"
	make_temporary_file "$target"
	temporary_file=$created_temporary_file
	printf '%s\n' "$text" >"$temporary_file"
	commit_temporary_file "$temporary_file" "$target" "$mode"
}

copy_live_config() {
	local source=$1 target=$2
	local temporary_file copied_size
	[[ -f $source && ! -L $source ]] || return 0
	[[ $(stat -c '%F' -- "$source") == 'regular file' ]] || die "unsafe live configuration source: $source"
	ensure_directory "$(dirname -- "$target")"
	make_temporary_file "$target"
	temporary_file=$created_temporary_file
	dd if="$source" of="$temporary_file" bs=1M count=17 iflag=nofollow status=none
	copied_size=$(stat -c '%s' -- "$temporary_file")
	((copied_size <= max_live_config_bytes)) || die "live configuration is too large: $source"
	commit_temporary_file "$temporary_file" "$target" 0644
}

copy_gnome_settings_to_homes() {
	local source=$1 home_directory user_name settings_directory settings_file user_ids
	local user_id group_id resolved_home
	[[ -f $source && ! -L $source ]] || return 0
	copy_live_config "$source" "$root_mount/etc/big-default-config/gnome-settings"
	copy_live_config "$source" "$root_mount/etc/skel/.config/dconf/settings.gnome"
	for home_directory in "$root_mount"/home/*; do
		[[ -d $home_directory && ! -L $home_directory ]] || continue
		resolved_home=$(realpath -e -- "$home_directory") || continue
		path_is_within_root "$resolved_home" || die "home directory escapes installation root: $home_directory"
		user_name=$(basename -- "$home_directory")
		[[ $user_name =~ ^[a-z_][a-z0-9_-]*[$]?$ ]] || continue
		user_ids=$(awk -F: -v user="$user_name" '$1 == user { print $3 ":" $4 }' "$root_mount/etc/passwd" 2>/dev/null || true)
		[[ $user_ids =~ ^[0-9]+:[0-9]+$ ]] || continue
		IFS=: read -r user_id group_id <<<"$user_ids"
		((user_id > 0)) || continue
		settings_directory=$home_directory/.config/dconf
		settings_file=$settings_directory/settings.gnome
		ensure_directory "$settings_directory"
		copy_live_config "$source" "$settings_file"
		chown "$user_id:$group_id" "$home_directory/.config" "$settings_directory" "$settings_file"
	done
}

current_gnome_settings_source() {
	local live_home_root=${1:-/home}
	local fallback=${2:-$live_state_directory/gnome-settings}
	local resolved_root home_directory candidate resolved_home resolved_candidate
	resolved_root=$(realpath -e -- "$live_home_root") || {
		printf '%s\n' "$fallback"
		return 0
	}
	for home_directory in "$resolved_root"/*; do
		[[ -d $home_directory && ! -L $home_directory ]] || continue
		resolved_home=$(realpath -e -- "$home_directory") || continue
		[[ $resolved_home == "$resolved_root/"* ]] || continue
		candidate=$home_directory/.config/dconf/settings.gnome
		[[ -f $candidate && ! -L $candidate ]] || continue
		resolved_candidate=$(realpath -e -- "$candidate") || continue
		[[ $resolved_candidate == "$resolved_home/"* ]] || continue
		printf '%s\n' "$resolved_candidate"
		return 0
	done
	printf '%s\n' "$fallback"
}

main() {
	local grub_file sddm_state config_directory session gnome_settings_source
	((EUID == 0)) || die 'this setup must run as root'
	load_kernel_options || die 'cannot load kernel option parser'
	root_mount=$(canonical_root_mount "${1:-}")
	grub_file=$root_mount/etc/default/grub
	sddm_state=$root_mount/var/lib/sddm/state.conf
	config_directory=$root_mount/etc/big-default-config

	[[ ! -e $grub_file ]] || write_grub_configuration "$grub_file"
	if kernel_has_argument wayland; then
		session=/usr/share/wayland-sessions/plasmawayland.desktop
	else
		session=/usr/share/xsessions/plasma.desktop
	fi
	atomic_write_text "$sddm_state" 0644 $'[Last]\nSession='"$session"
	ensure_directory "$config_directory"
	copy_live_config "$live_state_directory/desktop-theme" "$config_directory/theme"
	copy_live_config "$live_state_directory/desktop" "$config_directory/desktop"
	copy_live_config "$live_state_directory/gnome-layout" "$config_directory/gnome-layout"
	gnome_settings_source=$(current_gnome_settings_source /home)
	copy_gnome_settings_to_homes "$gnome_settings_source"
	copy_live_config "$live_state_directory/enable-jamesdsp" "$config_directory/jamesdsp"
	copy_live_config "$live_state_directory/improve-display" "$config_directory/display-profile"
	printf '%s\n' 'BigLinux installation setup completed successfully'
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
	main "$@"
fi
