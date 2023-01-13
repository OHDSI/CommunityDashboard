import { Injectable } from '@angular/core';
import { debounceTime, Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class IframeTokenBucketService {
  // This grants plot "tokens" to subscribers
  // using a throttled, leaky bucket, debounced, round robin strategy.
  // I was bored...

  _tokens = 3
  _subscribers: { [key: string]: () => void } = {}
  _plotDequeue: string[] = []
  _resizeQueue = new Subject()

  constructor(
  ) { 
    this._resizeQueue.pipe(
      debounceTime(2000),
    ).subscribe(() => {
      this._plotDequeue.push(...Object.keys(this._subscribers))
      setTimeout(() => this.roundRobin())
    })
  }

  queueResize() {
    this._resizeQueue.next(null)
  }

  _id = 0
  subscribePlotDequeue(next: () => void) {
    const id = this._id
    this._id += 1
    this._subscribers[`${id}`] = next
    // We can't debounce these even if we'd
    // like to in order to minimize traffic
    // during a resize. There's no good way
    // to know if this is a "real init" which should
    // have no delay, or a "resize init" which
    // should be debounced.
    this._plotDequeue.push(`${id}`)
    setTimeout(() => this.roundRobin())
    return id
  }

  unsubscribePlotDequeue(subscription: number) {
    delete this._subscribers[subscription]
  }

  _dequeueActive = false
  roundRobin() {
    if (!this._dequeueActive) {
      this._dequeueActive = true
      this._roundRobin()
    }
  }

  _roundRobin() {
    if (!this._plotDequeue.length || !this._tokens) {
      this._dequeueActive = false
      return
    }
    const id = this._plotDequeue.splice(0, 1)[0]
    if (id in this._subscribers) {
      this._tokens -= 1
      setTimeout(() => {
        this._tokens += 1
        if (this._tokens == 1) {
          this.roundRobin()
        }
      }, 2000)
      this._subscribers[id]()
    }
    this._roundRobin()
  }

}
