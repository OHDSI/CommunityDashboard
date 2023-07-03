import { ComponentFixture, TestBed } from '@angular/core/testing';

import { OpenSourceEcosystemComponent } from './open-source-ecosystem.component';

describe('OpenSourceEcosystemComponent', () => {
  let component: OpenSourceEcosystemComponent;
  let fixture: ComponentFixture<OpenSourceEcosystemComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [OpenSourceEcosystemComponent]
    });
    fixture = TestBed.createComponent(OpenSourceEcosystemComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
