;;; Winter AI -- Common Lisp Symbolic Reasoner (SBCL)
;;; Builds a symbolic frame (association list) from tokens.
;;; Scores exact keyword overlap against a corpus file.
;;; Usage: sbcl --script reasoner.lisp "<tokens-csv>" [corpus-file]
(defun split-csv (s)
  (let ((parts '()) (start 0))
    (loop for i from 0 to (length s)
          do (when (or (= i (length s)) (char= (char s i) #\,))
               (when (> i start) (push (subseq s start i) parts))
               (setf start (1+ i))))
    (nreverse parts)))

(defun read-file-lines (path)
  (handler-case
      (with-open-file (in path :direction :input :external-format :utf-8)
        (loop for line = (read-line in nil nil) while line collect line))
    (error () nil)))

(defun build-frame (tokens)
  (list (cons :token-count (length tokens))
        (cons :tokens tokens)
        (cons :has-question (if (member "?" tokens :test #'string=) t nil))))

(defun score-line (tokens line)
  (let* ((words (split-csv (substitute #\, #\Space (string-downcase line))))
         (hits (count-if (lambda (tok) (member tok words :test #'string=)) tokens)))
    hits))

(defun best-match (tokens lines)
  (reduce (lambda (a b) (if (> (car a) (car b)) a b))
          (mapcar (lambda (l) (cons (score-line tokens l) l)) lines)
          :initial-value (cons 0 "")))

(defun main ()
  (let* ((args (rest sb-ext:*posix-argv*))
         (tokens (if (>= (length args) 1) (split-csv (first args)) '()))
         (corpus-path (if (>= (length args) 2) (second args) nil))
         (lines (if corpus-path (read-file-lines corpus-path) '()))
         (frame (build-frame tokens))
         (match (if lines (best-match tokens lines) (cons 0 ""))))
    (format t "ENGINE: Common Lisp (SBCL)~%")
    (format t "FRAME: ~S~%" frame)
    (format t "MATCH-SCORE: ~A~%" (car match))
    (format t "MATCH-LINE: ~A~%" (string-trim '(#\Space #\Tab) (cdr match)))
    (format t "TRACE: (reduce max-score (mapcar score-line lines))~%")))

(main)
