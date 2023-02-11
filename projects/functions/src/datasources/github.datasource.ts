import {inject, lifeCycleObserver, LifeCycleObserver} from '@loopback/core';
import {juggler} from '@loopback/repository';
import SwaggerClient from 'swagger-client'
import {Request} from 'cross-fetch'

const RATE_LIMIT = 2000
const BUCKET_SIZE = 3

const config = {
  name: 'github',
  connector: 'openapi',
  // spec: 'https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.2022-11-28.yaml',
  spec: './specs/api.github.com.2022-11-28.yaml',
  validate: false,
  authorizations: {},
  positional: false,
};

class RateTokenBucket {

  _tokens = 3
  _tokenQueue: (() => unknown)[] = []

  http = (r: Request) => this.withRateToken(
    () => SwaggerClient.http(r)
  )
  
  withRateToken<T>(op: () => Promise<T>): Promise<T> {
    return new Promise((res, _) => {
      this._tokenQueue.push(
        () => res(op())
      )
      this.roundRobin()
    })
  }

  _dequeueActive = false
  roundRobin() {
    if (!this._dequeueActive) {
      this._dequeueActive = true
      this._roundRobin()
    }
  }

  _roundRobin() {
    if (!this._tokenQueue.length || !this._tokens) {
      this._dequeueActive = false
      return
    }
    this._tokens -= 1
    this.refreshTokens()
    const op = this._tokenQueue.splice(0, 1)[0]
    setTimeout(op)
    this._roundRobin()
  }

  _refreshTokensActive = false
  refreshTokens() {
    if (!this._refreshTokensActive) {
      this._refreshTokensActive = true
      setTimeout(() => this._refreshTokens(), RATE_LIMIT)
    }
  }

  _refreshTokens() {
    this._tokens += 1
    // If next op was waiting for a token
    // then reactivate queue.
    if (this._tokens === 1) {
      this.roundRobin()
    }
    if (this._tokens >= BUCKET_SIZE) {
      this._refreshTokensActive = false
    } else {
      setTimeout(() => this._refreshTokens(), RATE_LIMIT)
    }
  }
}

function withAuth(r: Request): Request {
  const modifiedRequest = r as unknown as { headers: { [key: string]: string}}
  const encoded = Buffer.from('natb1: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').toString('base64')
  modifiedRequest.headers['Authorization'] = `Basic ${encoded}`
  return modifiedRequest as unknown as Request
}

@lifeCycleObserver('datasource')
export class GitHubDataSource extends juggler.DataSource
  implements LifeCycleObserver {
  static dataSourceName = 'GitHub';
  static readonly defaultConfig = config;

  constructor(
    @inject('datasources.config.GitHub', {optional: true})
    dsConfig: object = config,
  ) {
    const rateTokenBucket = new RateTokenBucket()
    const rateLimitConfig = {
      httpClient: (r: Request) => rateTokenBucket.http(withAuth(r)),
      ...dsConfig
    }
    super(rateLimitConfig);
  }
}
