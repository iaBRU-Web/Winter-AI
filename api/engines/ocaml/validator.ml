(* Winter AI -- OCaml Input Validator (compiled native, real algebraic types) *)
type validation_result = Valid of string | TooLong of int | Empty | InvalidUtf8

let max_len = 4096

let is_valid_utf8 (s : string) : bool =
  let n = String.length s in
  let rec walk i =
    if i >= n then true
    else let c = Char.code s.[i] in
      if c < 0x80 then walk (i + 1)
      else if c land 0xE0 = 0xC0 && i+1 < n && Char.code s.[i+1] land 0xC0 = 0x80 then walk (i+2)
      else if c land 0xF0 = 0xE0 && i+2 < n && Char.code s.[i+1] land 0xC0 = 0x80 && Char.code s.[i+2] land 0xC0 = 0x80 then walk (i+3)
      else if c land 0xF8 = 0xF0 && i+3 < n && Char.code s.[i+1] land 0xC0 = 0x80 && Char.code s.[i+2] land 0xC0 = 0x80 && Char.code s.[i+3] land 0xC0 = 0x80 then walk (i+4)
      else false
  in walk 0

let normalise_ws (s : string) : string =
  let buf = Buffer.create (String.length s) in
  let last_ws = ref false in
  String.iter (fun c ->
    if c = ' ' || c = '\t' || c = '\n' || c = '\r' then begin
      if not !last_ws then Buffer.add_char buf ' '; last_ws := true
    end else begin Buffer.add_char buf c; last_ws := false end) s;
  String.trim (Buffer.contents buf)

let validate (raw : string) : validation_result =
  if String.length raw = 0 then Empty
  else if not (is_valid_utf8 raw) then InvalidUtf8
  else let cleaned = normalise_ws raw in
    if String.length cleaned = 0 then Empty
    else if String.length cleaned > max_len then TooLong (String.length cleaned)
    else Valid cleaned

let () =
  let raw = if Array.length Sys.argv > 1 then Sys.argv.(1) else "" in
  print_endline "ENGINE: OCaml (native, compiled)";
  (match validate raw with
   | Valid s -> Printf.printf "STATUS: valid\nNORMALISED: %s\nLENGTH: %d\n" s (String.length s)
   | TooLong n -> Printf.printf "STATUS: rejected\nREASON: too_long(%d)\n" n
   | Empty -> Printf.printf "STATUS: rejected\nREASON: empty\n"
   | InvalidUtf8 -> Printf.printf "STATUS: rejected\nREASON: invalid_utf8\n");
  Printf.printf "TRACE: match validate raw with Valid s | TooLong n | Empty | InvalidUtf8\n"
