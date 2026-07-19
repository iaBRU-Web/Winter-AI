#!/usr/bin/env guile
!#
;; Winter AI -- Scheme Decision Engine (GNU Guile)
;; Real (cond ...) dispatch over tokenised input.
;; Usage: guile decision.scm <lang> <token1,token2,...>
(use-modules (ice-9 regex) (srfi srfi-1))

(define greeting-words '((en . (hello hi hey greetings)) (fr . (bonjour salut bonsoir)) (rw . (muraho bite amakuru))))
(define thanks-words   '((en . (thanks thank appreciate)) (fr . (merci)) (rw . (murakoze))))
(define farewell-words '((en . (bye goodbye later)) (fr . (revoir)) (rw . (murabeho))))
(define identity-words '((en . (who name yourself are)) (fr . (qui appelles)) (rw . (witwa uri))))
(define wellbeing-words '((en . (how doing fine feeling)) (fr . (comment allez)) (rw . (amakuru bite))))
(define help-words     '((en . (help assist can support)) (fr . (aide aider)) (rw . (saidia))))
(define positive-words '(good great love happy excellent wonderful nice awesome perfect bien neza byiza superbe))
(define negative-words '(bad hate sad angry terrible awful horrible mauvais triste))

(define (str->symlist s)
  (map string->symbol (filter (lambda (x) (> (string-length x) 0)) (string-split s #\,))))

(define (intersect? tokens words) (not (null? (lset-intersection eq? tokens words))))

(define (words-for table lang)
  (let ((e (assq (string->symbol lang) table)))
    (if e (cdr e) '())))

(define (classify-intent tokens lang)
  (cond
    ((intersect? tokens (words-for greeting-words lang)) 'greeting)
    ((intersect? tokens (words-for thanks-words lang))   'thanks)
    ((intersect? tokens (words-for farewell-words lang)) 'farewell)
    ((intersect? tokens (words-for identity-words lang)) 'identity)
    ((intersect? tokens (words-for wellbeing-words lang)) 'wellbeing)
    ((intersect? tokens (words-for help-words lang))     'help)
    (else 'lookup)))

(define (sentiment-score tokens)
  (let ((pos (length (lset-intersection eq? tokens positive-words)))
        (neg (length (lset-intersection eq? tokens negative-words))))
    (cond ((> pos neg) 'positive) ((> neg pos) 'negative) (else 'neutral))))

(define (confidence tokens table lang intent)
  (if (eq? intent 'lookup) 0.35
    (let* ((w (words-for table lang))
           (hits (length (lset-intersection eq? tokens w))))
      (/ (exact->inexact hits) (max 1 (length tokens))))))

(define (main args)
  (let* ((lang   (if (> (length args) 1) (list-ref args 1) "en"))
         (raw    (if (> (length args) 2) (list-ref args 2) ""))
         (tokens (str->symlist raw))
         (intent (classify-intent tokens lang))
         (sent   (sentiment-score tokens))
         (table  (case intent
                   ((greeting) greeting-words) ((thanks) thanks-words)
                   ((farewell) farewell-words) ((identity) identity-words)
                   ((wellbeing) wellbeing-words) ((help) help-words)
                   (else greeting-words)))
         (conf   (confidence tokens table lang intent)))
    (display "ENGINE: Scheme (GNU Guile)") (newline)
    (display (string-append "INTENT: " (symbol->string intent))) (newline)
    (display (string-append "SENTIMENT: " (symbol->string sent))) (newline)
    (display (string-append "CONFIDENCE: " (number->string (exact->inexact conf)))) (newline)
    (display (string-append "TRACE: (cond ...) => '" (symbol->string intent))) (newline)))

(main (command-line))
