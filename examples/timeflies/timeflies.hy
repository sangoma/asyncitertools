(import [asyncio [ensure-future get-event-loop sleep]]
        [tkinter [Frame Label TclError Tk]]
        [observer [Observer]]
        [asyncitertools :as op])


(defmacro λ [&rest body]
  `(fn [it] ~@body))


(defmacro Σ [stream &rest body]
  `(for/a [it ~stream] ~@body))


(defmacro forever [&rest body]
  `(while True ~@body))


(defn/a position-label [label idx events]
  (Σ (->> events
          (op.delay (/ idx 20)))
     (.place label
             :x (+ it.x (* idx 10) 15)
             :y it.y)))


(defn/a main [&optional [loop None]]
  (setv mousemoves (Observer)
        root (Tk)
        frame (Frame :width 800 :height 600))

  (.title root "asyncitertools (hy)")
  (.bind frame "<Motion>" (λ (ensure-future (.send mousemoves it))))

  (setv tasks [])
  (for [[idx char] (enumerate "TIME FLIES LIKE AN ARROW")]
    (setv label (Label frame :text char))
    (.config label {"borderwidth" 0 "padx" 0 "pady" 0})
    (.append tasks (ensure-future (position-label label idx mousemoves))))

  (.pack frame)
  (try
    (forever (.update root) (await (sleep 0.0005)))
    (except [e TclError]
      (if (not (in "application has been destroyed" (. e args [0])))
          (raise)))
    (finally
      (for [task tasks] (.cancel task)))))


(defmain [&rest args]
  (.run-until-complete (get-event-loop) (main)))
